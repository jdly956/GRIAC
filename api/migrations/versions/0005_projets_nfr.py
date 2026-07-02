"""Entité Projet : contexte, NFR typées, dossiers documentaires (S1.11, D19).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-02

`project_dossiers` porte l'arbitrage A6 : l'association projet ↔ dossiers
documentaires faisant foi est celle confirmée par le PO (la suggestion S1.9
`documents.projet_suggere` n'est qu'une proposition). `origine` trace si
l'entrée vient d'une suggestion acceptée ou d'un ajout manuel du PO.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TYPES_NFR = (
    "performance",
    "volumetrie",
    "ssi",
    "rgpd",
    "accessibilite_rgaa",
    "disponibilite",
    "auditabilite",
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE projects (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            nom TEXT NOT NULL UNIQUE,
            contexte TEXT NOT NULL DEFAULT '',
            cree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
            modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE project_nfrs (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            type TEXT NOT NULL CHECK (type IN {TYPES_NFR!r}),
            formulation TEXT NOT NULL,
            valeur_cible TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE project_dossiers (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            dossier TEXT NOT NULL,
            origine TEXT NOT NULL DEFAULT 'po' CHECK (origine IN ('po', 'suggestion')),
            UNIQUE (project_id, dossier)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_dossiers")
    op.execute("DROP TABLE IF EXISTS project_nfrs")
    op.execute("DROP TABLE IF EXISTS projects")
