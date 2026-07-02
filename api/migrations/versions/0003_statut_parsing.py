"""Statut de parsing des documents (S1.8).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02

Statuts : a_parser (défaut), parse, echec, ocr_requis (PDF scanné — OCR au
sprint 2), hors_perimetre (extension non parsée). Le dérivé markdown vit hors
repo (derived/ ou S3) : la base n'en garde que le chemin.
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
            ADD COLUMN statut_parsing TEXT NOT NULL DEFAULT 'a_parser',
            ADD COLUMN chemin_derive TEXT,
            ADD COLUMN erreur_parsing TEXT,
            ADD COLUMN date_parsing TIMESTAMPTZ
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
            DROP COLUMN IF EXISTS statut_parsing,
            DROP COLUMN IF EXISTS chemin_derive,
            DROP COLUMN IF EXISTS erreur_parsing,
            DROP COLUMN IF EXISTS date_parsing
        """
    )
