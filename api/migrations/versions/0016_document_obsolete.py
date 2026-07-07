"""« Marquer obsolète » un document — R8 (refonte UX/UI, H10, arbitrage UX8).

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-07

Un document obsolète reste en base et à l'écran (badge, réversible) mais sort
des recherches E2 (`FILTRES_COMMUNS`) : c'est le statut « obsolète » promis par
l'écran A5 (E4) — l'alternative douce à la suppression définitive S3.17.
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN est_obsolete BOOLEAN NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS est_obsolete")
