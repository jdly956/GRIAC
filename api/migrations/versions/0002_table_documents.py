"""Table documents — inventaire du corpus (S1.7).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02

Clé d'idempotence du scan : le chemin relatif (UNIQUE). Le sha256 est indexé
pour la détection de doublons (S1.9) et la reprise sur hash (D9). Les colonnes
de qualification (projet, version, statut…) arrivent avec S1.9.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE documents (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            chemin TEXT NOT NULL UNIQUE,
            nom TEXT NOT NULL,
            extension TEXT NOT NULL,
            taille_octets BIGINT NOT NULL,
            sha256 TEXT NOT NULL,
            mtime TIMESTAMPTZ NOT NULL,
            premiere_vue TIMESTAMPTZ NOT NULL DEFAULT now(),
            derniere_vue TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_documents_sha256 ON documents (sha256)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS documents")
