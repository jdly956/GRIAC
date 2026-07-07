"""Inventaire des documents pour l'écran « mes documents » (E4.3, arbitrage A5).

Expose l'état du corpus tel que produit par le DAG d'ingestion : statut de
parsing (S1.8), référence/doublon (S1.9), projet suggéré (A6). Les stats
alimentent l'alerte « couverture faible » de l'écran ; le volet conversationnel
de cette alerte (moteur) est déjà couvert par l'avertissement « aucune source
récupérable » du RAG.
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sia_api.db import get_connexion
from sia_api.ingestion import dossier_corpus

router = APIRouter(tags=["documents"])

Connexion = Annotated[Any, Depends(get_connexion)]

REQUETE_LISTE = """
    SELECT id, chemin, nom, extension, statut_parsing, est_reference,
           doublon_de IS NOT NULL AS doublon, projet_suggere
    FROM documents ORDER BY chemin
"""

# S3.14 : la fiche document — tout ce que le pipeline a produit pour CE fichier.
REQUETE_FICHE = """
    SELECT id, chemin, nom, extension, taille_octets, sha256,
           statut_parsing, erreur_parsing,
           to_char(date_parsing, 'YYYY-MM-DD HH24:MI') AS date_parsing,
           chemin_derive, est_reference, doublon_de, projet_suggere,
           version_no, groupe_version
    FROM documents WHERE id = %(id)s
"""

REQUETE_CHUNKS = """
    SELECT ordinal, section, nb_tokens, contenu, embedding IS NOT NULL AS embarque
    FROM chunks WHERE document_chemin = %(chemin)s ORDER BY ordinal
"""

# Aperçu du dérivé markdown : assez pour juger le parsing, sans servir 2 Mo.
TAILLE_APERCU_DERIVE = 8_000

# Formats que le pipeline sait convertir en markdown (S3.16) : docling pour
# docx/pdf/pptx/xlsx, convertisseur eml dédié (stdlib) côté ingestion.
# Source unique — `sia_ingestion.parse` importe cette constante.
EXTENSIONS_PARSABLES = ("docx", "pdf", "pptx", "xlsx", "eml")
_LISTE_PARSABLES = ", ".join(f"'{extension}'" for extension in EXTENSIONS_PARSABLES)

REQUETE_STATS = f"""
    SELECT count(*) AS total,
           count(*) FILTER (WHERE extension IN ({_LISTE_PARSABLES})) AS parsables,
           count(*) FILTER (WHERE statut_parsing = 'parse') AS parses,
           count(*) FILTER (WHERE statut_parsing = 'echec') AS echecs,
           count(*) FILTER (WHERE statut_parsing = 'ocr_requis') AS ocr_requis,
           count(*) FILTER (WHERE est_reference) AS references
    FROM documents
"""


class DocumentInventaire(BaseModel):
    id: int  # S3.14 : l'inventaire pointe vers la fiche /documents/{id}
    chemin: str
    nom: str
    extension: str
    statut_parsing: str  # a_parser | parse (indexé) | echec | ocr_requis
    est_reference: bool
    doublon: bool
    projet_suggere: str | None


class ChunkDocument(BaseModel):
    ordinal: int
    section: str  # le fil de titres (traçabilité des citations E2)
    nb_tokens: int
    contenu: str
    embarque: bool  # embedding présent (nœud E)


class FicheDocument(BaseModel):
    id: int
    chemin: str
    nom: str
    extension: str
    taille_octets: int
    sha256: str
    statut_parsing: str
    erreur_parsing: str | None
    date_parsing: str | None
    chemin_derive: str | None
    derive_apercu: str | None  # début du markdown produit par docling/OCR
    derive_tronque: bool
    est_reference: bool
    doublon_de: str | None
    projet_suggere: str | None
    version_no: int | None
    groupe_version: str | None
    chunks: list[ChunkDocument]
    nb_chunks: int
    nb_embarques: int


class StatsDocuments(BaseModel):
    total: int
    parsables: int
    parses: int
    echecs: int
    ocr_requis: int
    references: int
    couverture_parsing: float  # parses / parsables — 1.0 si rien à parser


@router.get("/documents")
def lister_documents(connexion: Connexion) -> list[DocumentInventaire]:
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_LISTE)
        return [
            DocumentInventaire(
                id=ligne[0],
                chemin=ligne[1],
                nom=ligne[2],
                extension=ligne[3],
                statut_parsing=ligne[4],
                est_reference=ligne[5],
                doublon=ligne[6],
                projet_suggere=ligne[7],
            )
            for ligne in curseur.fetchall()
        ]


def _lire_apercu_derive(chemin_derive: str | None) -> tuple[str | None, bool]:
    """Début du dérivé markdown (fichier hors repo, écrit par le nœud parse).

    Fichier absent ou illisible (pod recréé, dérivés non régénérés) : on le dit
    plutôt que d'échouer — la fiche reste consultable.
    """
    if not chemin_derive:
        return None, False
    try:
        texte = Path(chemin_derive).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, False
    return texte[:TAILLE_APERCU_DERIVE], len(texte) > TAILLE_APERCU_DERIVE


@router.get("/documents/stats")
def stats_documents(connexion: Connexion) -> StatsDocuments:
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_STATS)
        total, parsables, parses, echecs, ocr, references = curseur.fetchone()
    return StatsDocuments(
        total=total,
        parsables=parsables,
        parses=parses,
        echecs=echecs,
        ocr_requis=ocr,
        references=references,
        couverture_parsing=round(parses / parsables, 3) if parsables else 1.0,
    )


# Enregistrée APRÈS /documents/stats : la route dynamique {document_id}
# capturerait « stats » sinon (ordre de matching FastAPI).
@router.get("/documents/{document_id}")
def fiche_document(document_id: int, connexion: Connexion) -> FicheDocument:
    """S3.14 : tout le traitement d'un document — parsing/OCR, dérivé, chunks."""
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_FICHE, {"id": document_id})
        ligne = curseur.fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail=f"Document {document_id} introuvable")
        curseur.execute(REQUETE_CHUNKS, {"chemin": ligne[1]})
        chunks = [
            ChunkDocument(ordinal=c[0], section=c[1], nb_tokens=c[2], contenu=c[3], embarque=c[4])
            for c in curseur.fetchall()
        ]
    apercu, tronque = _lire_apercu_derive(ligne[9])
    return FicheDocument(
        id=ligne[0],
        chemin=ligne[1],
        nom=ligne[2],
        extension=ligne[3],
        taille_octets=ligne[4],
        sha256=ligne[5],
        statut_parsing=ligne[6],
        erreur_parsing=ligne[7],
        date_parsing=ligne[8],
        chemin_derive=ligne[9],
        derive_apercu=apercu,
        derive_tronque=tronque,
        est_reference=ligne[10],
        doublon_de=ligne[11],
        projet_suggere=ligne[12],
        version_no=ligne[13],
        groupe_version=ligne[14],
        chunks=chunks,
        nb_chunks=len(chunks),
        nb_embarques=sum(1 for c in chunks if c.embarque),
    )


def _source_dans_corpus(chemin: str) -> Path | None:
    """Chemin (relatif au corpus, posé par le scan) -> fichier source, ou None.

    Garde-fou : un chemin qui sortirait de la racine corpus (donnée corrompue)
    est traité comme introuvable — jamais servi, jamais supprimé.
    """
    racine = dossier_corpus().resolve()
    source = (racine / chemin).resolve()
    if not source.is_relative_to(racine):
        return None
    return source if source.is_file() else None


@router.get("/documents/{document_id}/original")
def telecharger_original(document_id: int, connexion: Connexion) -> FileResponse:
    """S3.17 : le fichier source tel que déposé dans le corpus (D9 : jamais modifié)."""
    with connexion.cursor() as curseur:
        curseur.execute("SELECT chemin, nom FROM documents WHERE id = %(id)s", {"id": document_id})
        ligne = curseur.fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} introuvable")
    source = _source_dans_corpus(ligne[0])
    if source is None:
        raise HTTPException(
            status_code=404,
            detail=f"Original « {ligne[0]} » absent du corpus de ce pod "
            "(pod recréé ? le fichier source n'est pas dans le repo).",
        )
    return FileResponse(source, filename=ligne[1], media_type="application/octet-stream")


@router.delete("/documents/{document_id}", status_code=204)
def supprimer_document(document_id: int, connexion: Connexion) -> None:
    """S3.17 : suppression complète — base (chunks en cascade) ET fichiers disque.

    Le fichier source est retiré du corpus, sinon la prochaine indexation le
    ré-inventorierait (D9). Les documents qui pointaient ce chemin comme
    `doublon_de` sont repointés à NULL — la prochaine qualification retranche.
    Fichiers supprimés APRÈS le commit : une erreur base ne détruit rien.
    """
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT chemin, chemin_derive FROM documents WHERE id = %(id)s", {"id": document_id}
        )
        ligne = curseur.fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail=f"Document {document_id} introuvable")
        chemin, chemin_derive = ligne
        curseur.execute(
            "UPDATE documents SET doublon_de = NULL WHERE doublon_de = %(chemin)s",
            {"chemin": chemin},
        )
        curseur.execute("DELETE FROM documents WHERE id = %(id)s", {"id": document_id})
    connexion.commit()
    source = _source_dans_corpus(chemin)
    if source is not None:
        source.unlink(missing_ok=True)
    if chemin_derive:
        Path(chemin_derive).unlink(missing_ok=True)
