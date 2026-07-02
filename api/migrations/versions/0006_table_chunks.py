"""Table chunks — découpage des dérivés markdown (E1, nœud D).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-02

`sha256_document` porte la reprise sur hash (D9) : des chunks existants pour le
sha courant ne sont pas recalculés. La colonne `embedding vector(1024)` (bge-m3)
est remplie par le nœud E (embeddings) — NULL tant que non vectorisé.
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE chunks (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            document_chemin TEXT NOT NULL REFERENCES documents(chemin) ON DELETE CASCADE,
            sha256_document TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            section TEXT NOT NULL,
            contenu TEXT NOT NULL,
            nb_tokens INTEGER NOT NULL,
            embedding vector(1024),
            UNIQUE (document_chemin, ordinal)
        )
        """
    )
    op.execute("CREATE INDEX ix_chunks_document ON chunks (document_chemin)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunks")
