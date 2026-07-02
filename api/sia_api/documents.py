"""Inventaire des documents pour l'écran « mes documents » (E4.3, arbitrage A5).

Expose l'état du corpus tel que produit par le DAG d'ingestion : statut de
parsing (S1.8), référence/doublon (S1.9), projet suggéré (A6). Les stats
alimentent l'alerte « couverture faible » de l'écran ; le volet conversationnel
de cette alerte (moteur) est déjà couvert par l'avertissement « aucune source
récupérable » du RAG.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sia_api.db import get_connexion

router = APIRouter(tags=["documents"])

Connexion = Annotated[Any, Depends(get_connexion)]

REQUETE_LISTE = """
    SELECT chemin, nom, extension, statut_parsing, est_reference,
           doublon_de IS NOT NULL AS doublon, projet_suggere
    FROM documents ORDER BY chemin
"""

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
    chemin: str
    nom: str
    extension: str
    statut_parsing: str  # a_parser | parse (indexé) | echec | ocr_requis
    est_reference: bool
    doublon: bool
    projet_suggere: str | None


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
                chemin=ligne[0],
                nom=ligne[1],
                extension=ligne[2],
                statut_parsing=ligne[3],
                est_reference=ligne[4],
                doublon=ligne[5],
                projet_suggere=ligne[6],
            )
            for ligne in curseur.fetchall()
        ]


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
