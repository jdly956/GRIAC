"""Traçabilité persistée par message — S3.9 (A3 complet).

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-06

Fin de la « v1 assumée » S2.8 (sources/avertissements perdus au rechargement) :
chaque réponse du moteur persiste ses sources (avec **l'extrait exact** du
chunk cité — la promesse de l'arbitrage A3), ses avertissements et ses
divergences (A9), rattachés au message assistant du fil.
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE message_traces (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            message_id BIGINT NOT NULL REFERENCES workflow_messages(id) ON DELETE CASCADE,
            type TEXT NOT NULL CHECK (type IN ('source', 'avertissement', 'divergence')),
            nom TEXT,
            section TEXT,
            extrait TEXT,
            contenu TEXT,
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_message_traces_message ON message_traces (message_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS message_traces")
