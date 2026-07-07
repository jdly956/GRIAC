"""RAG — recherche hybride BM25 + vecteurs (E2, S2.3).

Mécanisme INTERNE au service du LLM accompagnant (arbitrage A1) : consommé par
le moteur de rédaction E3 à chaque étape ; l'endpoint REST n'existe que pour le
test et l'outillage, pas pour un écran de recherche autonome.

Deux volets sur les chunks : plein-texte français (`to_tsvector('french')`,
BM25 approché par ts_rank) et similarité cosinus pgvector (question vectorisée
via Albert, `encoding_format="float"` — gotcha S1.5), fusionnés par **RRF**
(Reciprocal Rank Fusion, k=60). Filtres : `est_reference` par défaut (statut
= référence, S1.9) et périmètre projet via les dossiers confirmés par le PO
(S1.11, arbitrage A6). Le volet vectoriel applique un SEUIL de distance cosinus
(`RECHERCHE_SEUIL_DISTANCE`) : sans lui, les K plus proches voisins « répondent »
à n'importe quelle question dès que le corpus est non vide, et l'avertissement
anti-invention ne peut jamais se déclencher (constaté sur pod, 03/07/2026).
Aucun résultat → avertissement explicite (anti-invention : une génération sans
source récupérable doit le signaler).
"""

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from sia_api.albert import creer_client
from sia_api.config import Settings, charger_settings
from sia_api.db import get_connexion

router = APIRouter(tags=["recherche"])

RRF_K = 60
LIMITE_PAR_VOLET = 30
# Part des chunks dans le budget global ≤ 20 000 tokens par requête (CLAUDE.md) :
# le reste est réservé au gabarit, au few-shot et au brief du PO (E3).
BUDGET_CONTEXTE_TOKENS = 6000
NB_CANDIDATS_RERANK = 15  # borne haute de l'assemblage E2 (8-15 chunks)

REQUETE_DOSSIERS_PROJET = "SELECT dossier FROM project_dossiers WHERE project_id = %(id)s"

FILTRES_COMMUNS = """
      AND (%(tout_statut)s OR d.est_reference)
      AND NOT d.est_obsolete
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
      AND (c.embedding <=> %(vecteur)s::vector) <= %(seuil)s
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
        curseur.execute(
            REQUETE_VECTEUR,
            {**parametres, "vecteur": vecteur, "seuil": settings.recherche_seuil_distance},
        )
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


def reranker(
    settings: Settings, question: str, contenus: list[str], http_post=None
) -> list[int] | None:
    """Ordre des candidats selon `/v1/rerank` d'Albert (bge-reranker-v2-m3).

    L'endpoint est HORS périmètre du SDK OpenAI ; schéma CONFIRMÉ par curl sur
    le pod Onyxia (03/07/2026, étape 0 du runbook s0) :
    {model, query, documents} -> results[{index, relevance_score}].
    Toute erreur => None : l'appelant conserve l'ordre RRF et le SIGNALE
    (jamais d'échec silencieux).
    """
    if http_post is None:  # résolu à l'appel : monkeypatchable, jamais de réseau en TU
        http_post = httpx.post
    try:
        reponse = http_post(
            settings.albert_base_url.rstrip("/") + "/rerank",
            headers={"Authorization": f"Bearer {settings.albert_api_key.get_secret_value()}"},
            json={
                "model": settings.albert_model_rerank,
                "query": question,
                "documents": contenus,
            },
            timeout=settings.albert_timeout_s,
        )
        reponse.raise_for_status()
        scores = reponse.json()["results"]
        return [
            element["index"]
            for element in sorted(scores, key=lambda element: -element["relevance_score"])
        ]
    except Exception:  # 404/422/réseau : repli RRF signalé par l'appelant
        return None


class SourceCitee(BaseModel):
    document: str
    nom: str
    section: str
    # S3.9 : l'extrait EXACT du chunk cité — la promesse de l'arbitrage A3
    # (« panneau sources avec extrait exact consultable »).
    extrait: str = ""


class ContexteResultat(BaseModel):
    contexte: str  # blocs « [Source : nom — section] » prêts pour le prompt E3
    sources: list[SourceCitee]
    nb_tokens: int
    rerank_applique: bool
    avertissement: str | None = None


def assembler_contexte(
    chunks: list[ChunkTrouve], budget_tokens: int = BUDGET_CONTEXTE_TOKENS
) -> tuple[str, list[ChunkTrouve], int]:
    """8–15 chunks max dans le budget ; chaque bloc porte sa citation (traçabilité).

    S3.20 (session 12) : plus de passe-droit du premier chunk — l'ancien
    `if retenus and …` embarquait TOUJOURS le premier chunk, même à ~235k
    tokens (chunk-tableau xlsx). Un chunk qui dépasse à lui seul le budget est
    tronqué à la borne et marqué ; le chunking S3.19 borne désormais les
    tableaux, ceci est la ceinture de sécurité côté E2 (l'extrait tronqué est
    aussi ce qui part en traçabilité S3.9 — les pages restent légères).
    """
    retenus: list[ChunkTrouve] = []
    total = 0
    for chunk in chunks[:NB_CANDIDATS_RERANK]:
        if not retenus and chunk.nb_tokens > budget_tokens:
            contenu = chunk.contenu[: budget_tokens * 4].rstrip() + (
                f"\n[… extrait tronqué : chunk de {chunk.nb_tokens} tokens > budget "
                f"{budget_tokens} — document à re-chunker (S3.19)]"
            )
            retenus.append(chunk.model_copy(update={"contenu": contenu}))
            total = budget_tokens
            break  # le budget est consommé — inutile d'empiler derrière
        if total + chunk.nb_tokens > budget_tokens:
            break
        retenus.append(chunk)
        total += chunk.nb_tokens
    blocs = [f"[Source : {chunk.nom} — {chunk.section}]\n{chunk.contenu}" for chunk in retenus]
    return "\n\n---\n\n".join(blocs), retenus, total


def construire_contexte(
    connexion, client, settings: Settings, entree: RechercheEntree, http_post=None
) -> ContexteResultat:
    """Recherche hybride -> rerank (repli RRF signalé) -> assemblage cité (E2 complet)."""
    candidats = rechercher(
        connexion, client, settings, entree.model_copy(update={"nb": NB_CANDIDATS_RERANK})
    )
    if not candidats.resultats:
        return ContexteResultat(
            contexte="",
            sources=[],
            nb_tokens=0,
            rerank_applique=False,
            avertissement=candidats.avertissement,
        )

    ordre = reranker(
        settings, entree.question, [chunk.contenu for chunk in candidats.resultats], http_post
    )
    rerank_applique = ordre is not None
    ordonnes = (
        [candidats.resultats[i] for i in ordre if i < len(candidats.resultats)]
        if rerank_applique
        else candidats.resultats
    )

    contexte, retenus, total = assembler_contexte(ordonnes[: entree.nb])
    return ContexteResultat(
        contexte=contexte,
        sources=[
            SourceCitee(
                document=chunk.document,
                nom=chunk.nom,
                section=chunk.section,
                extrait=chunk.contenu,
            )
            for chunk in retenus
        ],
        nb_tokens=total,
        rerank_applique=rerank_applique,
        avertissement=(
            None if rerank_applique else "Rerank indisponible : ordre de la fusion RRF conservé."
        ),
    )


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


@router.post("/contexte")
def contexte_route(
    entree: RechercheEntree, connexion: Connexion, albert: Albert
) -> ContexteResultat:
    """Contexte assemblé et cité, prêt à injecter dans le prompt (consommé par E3)."""
    client, settings = albert
    return construire_contexte(connexion, client, settings, entree)
