"""Consommation de tokens Albert — S3.11 (lot pré-pilote).

Lecture du registre `conso_tokens` (alimenté par le moteur E3 pour le chat et
par le nœud E de l'ingestion pour les embeddings) : conso d'une session
(affichée sur l'écran session) et agrégats pour la télémétrie, avec la jauge
du jour face au quota **tpd** relevé en S1.5 (2,46 M par défaut, surchargeable
par `ALBERT_TPD_QUOTA` si le quota réel change).
"""

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sia_api.db import get_connexion

router = APIRouter(tags=["conso"])

Connexion = Annotated[Any, Depends(get_connexion)]

# Quota quotidien relevé en S1.5 (GET /v1/me/info) — surchargeable si le quota
# réel change, sans redéploiement de code.
TPD_QUOTA_DEFAUT = 2_460_000


def _tpd_quota() -> int:
    return int(os.environ.get("ALBERT_TPD_QUOTA", TPD_QUOTA_DEFAUT))


class ConsoSession(BaseModel):
    appels: int
    tokens_entree: int
    tokens_sortie: int


class ConsoSource(BaseModel):
    source: str
    tokens_entree: int
    tokens_sortie: int


class ConsoTokens(BaseModel):
    total_entree: int
    total_sortie: int
    jour_total: int  # entrée + sortie du jour — la matière de la jauge tpd
    tpd_quota: int
    jour_part_tpd: float  # 0.0–1.0 (peut dépasser 1.0 si quota crevé)
    par_source: list[ConsoSource]


@router.get("/workflows/{session_id}/conso")
def conso_session(session_id: int, connexion: Connexion) -> ConsoSession:
    """Conso d'une session — session inconnue ou sans appel = zéros (pas de 404 :
    l'écran session l'affiche en simple indication)."""
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT count(*), coalesce(sum(tokens_entree), 0), coalesce(sum(tokens_sortie), 0) "
            "FROM conso_tokens WHERE session_id = %(id)s",
            {"id": session_id},
        )
        appels, entree, sortie = curseur.fetchone()
    return ConsoSession(appels=appels, tokens_entree=entree, tokens_sortie=sortie)


@router.get("/telemetrie/tokens")
def conso_globale(connexion: Connexion) -> ConsoTokens:
    tpd_quota = _tpd_quota()
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT coalesce(sum(tokens_entree), 0), coalesce(sum(tokens_sortie), 0) "
            "FROM conso_tokens"
        )
        total_entree, total_sortie = curseur.fetchone()
        curseur.execute(
            "SELECT coalesce(sum(tokens_entree + tokens_sortie), 0) FROM conso_tokens "
            "WHERE cree_le >= date_trunc('day', now())"
        )
        jour_total = curseur.fetchone()[0]
        curseur.execute(
            "SELECT source, coalesce(sum(tokens_entree), 0), coalesce(sum(tokens_sortie), 0) "
            "FROM conso_tokens GROUP BY source ORDER BY source"
        )
        par_source = [
            ConsoSource(source=ligne[0], tokens_entree=ligne[1], tokens_sortie=ligne[2])
            for ligne in curseur.fetchall()
        ]
    return ConsoTokens(
        total_entree=total_entree,
        total_sortie=total_sortie,
        jour_total=jour_total,
        tpd_quota=tpd_quota,
        jour_part_tpd=round(jour_total / tpd_quota, 4) if tpd_quota else 0.0,
        par_source=par_source,
    )
