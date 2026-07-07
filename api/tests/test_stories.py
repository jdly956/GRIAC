"""Tests S3.13 : stories d'une session — contenu + édition (la version éditée gagne)."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app

US = "**US — Consulter mon dossier**\n\n**En tant que** usager"


class FauxCurseur:
    def __init__(self, resultats: deque) -> None:
        self.resultats = resultats
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres or {}))

    def fetchone(self):
        return self.resultats.popleft()

    def fetchall(self):
        return self.resultats.popleft()

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, resultats: list) -> None:
        self.curseur = FauxCurseur(deque(resultats))
        self.commits = 0

    def cursor(self):
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


client = TestClient(app)


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> FausseConnexion:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        return connexion

    yield _brancher
    app.dependency_overrides.clear()


def test_contenus_version_editee_prioritaire(brancher) -> None:
    brancher(
        [
            [("assistant", "redaction", f"---\n{US}\n---")],  # messages
            [("Consulter mon dossier", "version éditée")],  # éditions
        ]
    )
    corps = client.get("/workflows/7/stories/contenus").json()
    assert corps == [
        {"titre": "Consulter mon dossier", "contenu": "version éditée", "editee": True}
    ]


def test_contenus_sans_edition(brancher) -> None:
    brancher([[("assistant", "redaction", f"---\n{US}\n---")], []])
    corps = client.get("/workflows/7/stories/contenus").json()
    assert corps[0]["editee"] is False
    assert "**En tant que** usager" in corps[0]["contenu"]


def test_edition_upsert(brancher) -> None:
    connexion = brancher([(7,)])  # la session existe
    corps = client.put(
        "/workflows/7/stories/edition",
        json={"titre": "Consulter mon dossier", "contenu": "nouvelle version"},
    ).json()
    assert corps["editee"] is True
    requete, params = next((r, p) for r, p in connexion.curseur.requetes if "story_editions" in r)
    assert "ON CONFLICT (session_id, titre)" in requete  # ré-édition = remplacement
    assert params["contenu"] == "nouvelle version"
    assert connexion.commits == 1


def test_edition_session_inconnue_404(brancher) -> None:
    brancher([None])
    reponse = client.put("/workflows/99/stories/edition", json={"titre": "X", "contenu": "Y"})
    assert reponse.status_code == 404
