"""RAG — recherche hybride BM25 + vecteurs (E2, S2.3).

Mécanisme INTERNE au service du LLM accompagnant (arbitrage A1) : consommé par
le moteur de rédaction E3 à chaque étape ; l'endpoint REST n'existe que pour le
test et l'outillage, pas pour un écran de recherche autonome.

Deux volets sur les chunks : plein-texte français (`to_tsvector('french')`,
BM25 approché par ts_rank) et similarité cosinus pgvector (question vectorisée
via Albert, `encoding_format="float"` — gotcha S1.5), fusionnés par **RRF**
(Reciprocal Rank Fusion, k=60). Filtres : `est_reference` par défaut (statut
= référence, S1.9) et périmètre projet via les dossiers confirmés par le PO
(S1.11, arbitrage A6). Aucun résultat → avertissement explicite (anti-invention :
une génération sans source récupérable doit le signaler).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from sia_api.albert import creer_client
from sia_api.config import Settings, charger_settings
from sia_api.db import get_connexion

router = APIRouter(tags=["recherche"])

RRF_K = 60
LIMITE_PAR_VOLET = 30

REQUETE_DOSSIERS_PROJET = "SELECT dossier FROM project_dossiers WHERE project_id = %(id)s"

FILTRES_COMMUNS = """
      AND (%(tout_statut)s OR d.est_reference)
      AND (%(dossiers)s::text[] IS NULL OR d.projet_suggere = ANY(%(dossiers)s::text[]))
"""

REQUETE_BM25 = f"""
    SELECT c.id
    FROM chunks c
    JOIN documents d ON d.chemin = c.document_chemin
    WHERE to_tsvector('french', c.contenu) @@ plainto_tsquery('french', %(question)s)
      {FILTRES_COMMUNS}
    ORDER BY ts_rank(to_tsvector('french', c.contenu),
                     plainto_tsquery('french', %(question)s)) DESC
    LIMIT %(limite)s
"""

REQUETE_VECTEUR = f"""
    SELECT c.id
    FROM chunks c
    JOIN documents d ON d.chemin = c.document_chemin
    WHERE c.embedding IS NOT NULL
      {FILTRES_COMMUNS}
    ORDER BY c.embedding <=> %(vecteur)s::vector
    LIMIT %(limite)s
"""

REQUETE_DETAILS = """
    SELECT c.id, c.document_chemin, d.nom, c.section, c.contenu, c.nb_tokens
    FROM chunks c
    JOIN documents d ON d.chemin = c.document_chemin
    WHERE c.id = ANY(%(ids)s)
"""


class RechercheEntree(BaseModel):
    question: str = Field(min_length=1)
    projet_id: int | None = None
    seulement_references: bool = True  # statut = référence (S1.9) par défaut
    nb: int = Field(10, ge=1, le=15)  # 8-15 chunks assemblés en E2/S2.4


class ChunkTrouve(BaseModel):
    document: str  # chemin — la citation porte document + section
    nom: str
    section: str
    contenu: str
    nb_tokens: int
    score_rrf: float


class RechercheResultat(BaseModel):
    resultats: list[ChunkTrouve]
    avertissement: str | None = None


def fusion_rrf(classements: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Fusion de classements par Reciprocal Rank Fusion — fonction pure."""
    scores: dict[int, float] = {}
    for classement in classements:
        for rang, identifiant in enumerate(classement, start=1):
            scores[identifiant] = scores.get(identifiant, 0.0) + 1.0 / (k + rang)
    return sorted(scores.items(), key=lambda element: (-element[1], element[0]))


def _vectoriser_question(client, settings: Settings, question: str) -> str:
    reponse = client.embeddings.create(
        model=settings.albert_model_embeddings,
        input=[question],
        encoding_format="float",  # gotcha Albert (S1.5)
    )
    return "[" + ",".join(repr(valeur) for valeur in reponse.data[0].embedding) + "]"


def rechercher(connexion, client, settings: Settings, entree: RechercheEntree) -> RechercheResultat:
    with connexion.cursor() as curseur:
        dossiers = None
        if entree.projet_id is not None:
            curseur.execute(REQUETE_DOSSIERS_PROJET, {"id": entree.projet_id})
            dossiers = [ligne[0] for ligne in curseur.fetchall()] or None

        parametres = {
            "question": entree.question,
            "tout_statut": not entree.seulement_references,
            "dossiers": dossiers,
            "limite": LIMITE_PAR_VOLET,
        }
        curseur.execute(REQUETE_BM25, parametres)
        classement_bm25 = [ligne[0] for ligne in curseur.fetchall()]

        vecteur = _vectoriser_question(client, settings, entree.question)
        curseur.execute(REQUETE_VECTEUR, {**parametres, "vecteur": vecteur})
        classement_vecteur = [ligne[0] for ligne in curseur.fetchall()]

        fusion = fusion_rrf([classement_bm25, classement_vecteur])[: entree.nb]
        if not fusion:
            return RechercheResultat(
                resultats=[],
                avertissement=(
                    "Aucune source récupérable dans le corpus pour cette question — "
                    "toute génération devra le signaler (anti-invention)."
                ),
            )

        scores = dict(fusion)
        curseur.execute(REQUETE_DETAILS, {"ids": list(scores)})
        par_id = {
            ligne[0]: ChunkTrouve(
                document=ligne[1],
                nom=ligne[2],
                section=ligne[3],
                contenu=ligne[4],
                nb_tokens=ligne[5],
                score_rrf=round(scores[ligne[0]], 6),
            )
            for ligne in curseur.fetchall()
        }
    resultats = [par_id[identifiant] for identifiant, _ in fusion if identifiant in par_id]
    return RechercheResultat(resultats=resultats)


def get_albert() -> tuple[Any, Settings]:
    """Client Albert par requête — surchargé par les tests (dependency_overrides)."""
    settings = charger_settings()
    return creer_client(settings), settings


Connexion = Annotated[Any, Depends(get_connexion)]
Albert = Annotated[tuple[Any, Settings], Depends(get_albert)]


@router.post("/recherche")
def rechercher_route(
    entree: RechercheEntree, connexion: Connexion, albert: Albert
) -> RechercheResultat:
    client, settings = albert
    return rechercher(connexion, client, settings, entree)
