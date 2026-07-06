"""Levée proposée d'une hypothèse — rapprochement décision d'interview ↔ registre (A8).

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-06

Constaté en session de validation Onyxia (06/07/2026, session réelle 8) : une
réponse d'interview du PO tranche souvent une [HYPOTHÈSE À VALIDER] déjà au
registre, mais celle-ci reste « en_attente » jusqu'à ce que le PO la retrouve
et clique. Le moteur PROPOSE désormais la levée : `statut_propose` porte la
suggestion (confirmée/rejetée) et sa justification — le champ `statut`, seul
porteur de l'invariant A8, n'est JAMAIS touché par cette proposition : la
décision individuelle du PO reste l'unique chemin de levée.
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE workflow_hypotheses
            ADD COLUMN statut_propose TEXT
                CHECK (statut_propose IN ('confirmee', 'rejetee')),
            ADD COLUMN justification_proposee TEXT,
            ADD COLUMN proposee_le TIMESTAMPTZ
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE workflow_hypotheses
            DROP COLUMN IF EXISTS statut_propose,
            DROP COLUMN IF EXISTS justification_proposee,
            DROP COLUMN IF EXISTS proposee_le
        """
    )
