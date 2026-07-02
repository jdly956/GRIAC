"""Sessions du workflow de rédaction — machine à états du prompt 3 (E3.1).

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-02

`workflow_hypotheses.origine` porte le marquage A3 (corpus cité / déclaré PO /
hypothèse modèle). `statut` porte l'invariant A8 : une hypothèse ne quitte
`en_attente` que par décision individuelle explicite — jamais par une
validation globale d'étape.
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

ETAPES = (
    "recuperation_feature",
    "interview",
    "stories_candidates",
    "redaction",
    "controle_dor",
    "synthese",
)


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE workflow_sessions (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            projet_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
            etape TEXT NOT NULL DEFAULT 'recuperation_feature' CHECK (etape IN {ETAPES!r}),
            feature TEXT NOT NULL,
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
            modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE workflow_hypotheses (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
            texte TEXT NOT NULL,
            origine TEXT NOT NULL DEFAULT 'modele' CHECK (origine IN ('corpus', 'po', 'modele')),
            statut TEXT NOT NULL DEFAULT 'en_attente'
                CHECK (statut IN ('en_attente', 'confirmee', 'rejetee')),
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
            decidee_le TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE workflow_messages (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('po', 'assistant')),
            etape TEXT NOT NULL,
            contenu TEXT NOT NULL,
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workflow_messages")
    op.execute("DROP TABLE IF EXISTS workflow_hypotheses")
    op.execute("DROP TABLE IF EXISTS workflow_sessions")
