"""Archivage des projets — R9 (refonte UX/UI, arbitrage UX8).

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-07

Un projet archivé disparaît des listes (et du choix à la création de session)
sans rien détruire — réversible. La suppression définitive, elle, s'appuie sur
les FK existantes : NFR et dossiers partent en cascade (0005), les sessions
liées passent à projet_id NULL (0008, SET NULL — arbitrage H9 du 07/07/2026 :
« suppression libre, sessions orphelines », le moteur continue sans contexte
projet comme pour toute session créée sans projet).
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE projects ADD COLUMN archive BOOLEAN NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS archive")
