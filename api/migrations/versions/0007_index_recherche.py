"""Index de recherche hybride (E2, S2.3).

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-02

GIN sur le tsvector français des chunks (volet BM25). Pas d'index ivfflat sur
les embeddings à ce stade : la recherche exacte suffit à l'échelle du POC —
à ajouter quand le vrai corpus donnera la volumétrie (lists à calibrer).
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING GIN (to_tsvector('french', contenu))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
