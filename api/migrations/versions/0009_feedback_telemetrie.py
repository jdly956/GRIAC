"""Feedback par story et matière première de la télémétrie (E4.4).

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-02

`story_feedbacks` porte la note 1-5 + commentaire par story (CLAUDE.md E4).
`workflow_validations` journalise chaque Oui/Non d'étape (règle 5) : la part
des « Non » sert de proxy v0 au taux d'édition — sans comptes (A7) ni accès
Jira (D10), les indicateurs d'usage sont des proxys assumés et documentés.
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE story_feedbacks (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
            story_titre TEXT NOT NULL,
            note SMALLINT NOT NULL CHECK (note BETWEEN 1 AND 5),
            commentaire TEXT NOT NULL DEFAULT '',
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE workflow_validations (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
            etape TEXT NOT NULL,
            valide BOOLEAN NOT NULL,
            commentaire TEXT NOT NULL DEFAULT '',
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workflow_validations")
    op.execute("DROP TABLE IF EXISTS story_feedbacks")
