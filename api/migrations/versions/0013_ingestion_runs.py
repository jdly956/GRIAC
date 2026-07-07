"""Runs d'ingestion — S3.10 (lot pré-pilote) : le pipeline depuis l'UI.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-06

Chaque « Indexer maintenant » crée un run ; l'orchestrateur
(`sia_ingestion.pipeline`) y consigne l'avancement nœud par nœud (rapport
JSONB mis à jour au fil de l'eau — l'écran de suivi lit en direct).
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ingestion_runs (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            statut TEXT NOT NULL DEFAULT 'en_cours'
                CHECK (statut IN ('en_cours', 'termine', 'echec_partiel', 'echec')),
            corpus TEXT NOT NULL,
            rapport JSONB NOT NULL DEFAULT '{}'::jsonb,
            demarre_le TIMESTAMPTZ NOT NULL DEFAULT now(),
            termine_le TIMESTAMPTZ
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingestion_runs")
