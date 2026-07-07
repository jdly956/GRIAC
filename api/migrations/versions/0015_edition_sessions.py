"""Édition des stories + gestion des sessions — S3.13 (lot pré-pilote).

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-06

- `story_editions` : la version ÉDITÉE par le PO d'une story (clé = titre,
  promesse de la cible E4 jamais livrée jusqu'ici) — elle GAGNE à l'export ;
- `workflow_sessions.titre` : nom libre affiché à l'accueil (sinon l'aperçu
  de la Feature) ; `archivee` : masquée de l'accueil, jamais supprimée
  (pas de destruction de données au MVP).
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE story_editions (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
            titre TEXT NOT NULL,
            contenu TEXT NOT NULL,
            modifie_le TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (session_id, titre)
        )
        """
    )
    op.execute(
        "ALTER TABLE workflow_sessions ADD COLUMN titre TEXT, "
        "ADD COLUMN archivee BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE workflow_sessions DROP COLUMN IF EXISTS titre, DROP COLUMN IF EXISTS archivee"
    )
    op.execute("DROP TABLE IF EXISTS story_editions")
