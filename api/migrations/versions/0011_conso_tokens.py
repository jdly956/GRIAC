"""Comptabilité des tokens Albert — S3.11 (lot pré-pilote).

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-06

Registre unique de consommation : chaque appel chat (rattaché à sa session)
et chaque lot d'embeddings (ingestion) y verse son `usage`. La contrainte
produit derrière : le quota **tpd 2,46 M** relevé en S1.5 — la télémétrie
affiche la jauge du jour. `session_id` en SET NULL : la conso survit à la
suppression d'une session (le quota est global).
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE conso_tokens (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source TEXT NOT NULL CHECK (source IN ('chat', 'embeddings')),
            session_id BIGINT REFERENCES workflow_sessions(id) ON DELETE SET NULL,
            modele TEXT NOT NULL,
            tokens_entree INTEGER NOT NULL DEFAULT 0,
            tokens_sortie INTEGER NOT NULL DEFAULT 0,
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS conso_tokens")
