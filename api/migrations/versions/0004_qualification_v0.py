"""Qualification v0 des documents — métadonnées, versions, doublons (S1.9).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-02

`projet_suggere` est une SUGGESTION (1er niveau du chemin, D7/S1.9) : l'association
faisant foi est celle confirmée par le PO via S1.11 (arbitrage A6). `est_reference`
alimente le filtre « statut = référence » du RAG (E2). `doublon_de` pointe le chemin
du document canonique de même sha256.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
            ADD COLUMN projet_suggere TEXT,
            ADD COLUMN date_nom DATE,
            ADD COLUMN version_no INTEGER,
            ADD COLUMN marque_finale BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN statut_brouillon BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN groupe_version TEXT,
            ADD COLUMN est_reference BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN doublon_de TEXT
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
            DROP COLUMN IF EXISTS projet_suggere,
            DROP COLUMN IF EXISTS date_nom,
            DROP COLUMN IF EXISTS version_no,
            DROP COLUMN IF EXISTS marque_finale,
            DROP COLUMN IF EXISTS statut_brouillon,
            DROP COLUMN IF EXISTS groupe_version,
            DROP COLUMN IF EXISTS est_reference,
            DROP COLUMN IF EXISTS doublon_de
        """
    )
