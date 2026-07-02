"""Accès PostgreSQL de l'API (S1.11).

Connexion par requête via une dépendance FastAPI ; l'URL vient exclusivement
de DATABASE_URL (jamais en dur — même règle que les migrations et l'ingestion).
Les tests unitaires surchargent `get_connexion` (dependency_overrides) : aucun
test ne touche une base réelle.
"""

import os
from collections.abc import Iterator

import psycopg
from fastapi import HTTPException


def get_connexion() -> Iterator[psycopg.Connection]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail=(
                "DATABASE_URL absente : les routes projets exigent PostgreSQL. "
                "En stack locale : make dev (le compose la fournit) ; hors compose, "
                "exporter DATABASE_URL — jamais en dur (CLAUDE.md)."
            ),
        )
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(database_url) as connexion:
        yield connexion
