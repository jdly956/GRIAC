"""Paramètres d'instance — S3.12 (lot pré-pilote).

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-06

Réglages globaux de l'instance partagée (A7 : sans comptes), clé/valeur.
Premier usage : `modele_chat` — le modèle de chat actif, changeable depuis
l'écran Paramètres **sans relance** (le moteur lit la surcharge à chaque
appel). Précédence : surcharge UI (cette table) > `ALBERT_MODEL_CHAT`
(env, réglage d'infra au démarrage) > défaut du code.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE parametres (
            cle TEXT PRIMARY KEY,
            valeur TEXT NOT NULL,
            modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS parametres")
