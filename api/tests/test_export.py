"""Tests E5 : extraction/dédup des stories, CSV Jira, markdown avec récap A8."""

import csv
import io
from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.export import extraire_stories_session, generer_csv_jira, generer_markdown
from sia_api.main import app

US_A = "**US — Consulter mon dossier**\n\n**En tant que** usager"
US_A_V2 = "**US — Consulter mon dossier**\n\n**En tant que** usager connecté (v2)"
US_B = "**US — Déposer une pièce**\n\n**En tant que** usager"


def _message(contenu: str, etape: str = "redaction", role: str = "assistant"):
    texte = f"Voici la story :\n\n---\n{contenu}\n---\n\nCette version convient-elle ?"
    return (role, etape, texte)


def test_extraction_et_dedup_la_derniere_version_gagne() -> None:
    messages = [
        _message(US_A),
        _message(US_B),
        _message(US_A_V2),  # itération règle 5 sur le même titre
        ("po", "redaction", "oui"),
        ("assistant", "interview", f"---\n{US_B}\n---"),  # hors étapes de rédaction : ignoré
    ]
    stories = extraire_stories_session(messages)
    assert len(stories) == 2
    assert any("(v2)" in story for story in stories)  # la dernière version remplace la première
    assert all("(v2)" in story or "Déposer" in story for story in stories)


def test_csv_jira_importable() -> None:
    contenu = generer_csv_jira([US_A, US_B])
    lignes = list(csv.reader(io.StringIO(contenu)))
    assert lignes[0] == ["Summary", "Issue Type", "Description"]
    assert lignes[1][0] == "Consulter mon dossier"
    assert lignes[1][1] == "Story"
    assert "**En tant que** usager" in lignes[1][2]
    assert len(lignes) == 3


def test_markdown_recapitule_les_hypotheses_a8() -> None:
    markdown = generer_markdown([US_A], ["Seuil 10 Mo [HYPOTHÈSE À VALIDER]"])
    assert "1 hypothèse(s) non levée(s)" in markdown
    assert "arbitrage A8" in markdown
    assert "> - Seuil 10 Mo" in markdown
    assert "NON CONFORME au gabarit" in markdown  # US_A est volontairement incomplète


def test_markdown_sans_hypothese_sans_avertissement() -> None:
    markdown = generer_markdown([US_A], [])
    assert "hypothèse(s) non levée(s)" not in markdown


# --- endpoints (DB scriptée) ---


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

    def cursor(self):
        return self.curseur


client = TestClient(app)


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> None:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion

    yield _brancher
    app.dependency_overrides.clear()


SCRIPT_AVEC_STORIES = [
    (7,),  # session existe
    [("assistant", "redaction", f"---\n{US_A}\n---")],  # messages
    [("Seuil 10 Mo [HYPOTHÈSE À VALIDER]",)],  # hypothèses en attente
]


def test_endpoint_csv(brancher) -> None:
    brancher(list(SCRIPT_AVEC_STORIES))
    reponse = client.get("/workflows/7/export/jira.csv")
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/csv")
    assert reponse.headers["x-hypotheses-non-levees"] == "1"  # avertissement A8
    assert reponse.text.startswith('"Summary","Issue Type","Description"')


def test_endpoint_markdown(brancher) -> None:
    brancher(list(SCRIPT_AVEC_STORIES))
    reponse = client.get("/workflows/7/export/markdown")
    assert reponse.status_code == 200
    assert "arbitrage A8" in reponse.text
    assert "**US — Consulter mon dossier**" in reponse.text


def test_endpoint_sans_story_409(brancher) -> None:
    brancher([(7,), [("po", "interview", "bonjour")]])
    reponse = client.get("/workflows/7/export/jira.csv")
    assert reponse.status_code == 409
    assert "Aucune story rédigée" in reponse.json()["detail"]


def test_endpoint_session_inconnue_404(brancher) -> None:
    brancher([None])
    assert client.get("/workflows/99/export/markdown").status_code == 404
