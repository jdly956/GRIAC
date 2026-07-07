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
from pydantic import BaseModel

from sia_api.db import get_connexion

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

REQUETE_STATS = """
    SELECT count(*) AS total,
           count(*) FILTER (WHERE extension IN ('docx', 'pdf')) AS parsables,
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
