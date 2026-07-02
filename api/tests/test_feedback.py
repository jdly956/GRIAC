"""Tests S2.10 : feedback par story + télémétrie (E4.4) — DB simulée."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app

client = TestClient(app)

US_A = "**US — Consulter mon dossier**\n\n**En tant que** usager"


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


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> FausseConnexion:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        return connexion

    yield _brancher
    app.dependency_overrides.clear()


def test_noter_une_story(brancher) -> None:
    connexion = brancher([(7,), (12,)])  # session existe ; INSERT RETURNING id
    reponse = client.post(
        "/workflows/7/feedback",
        json={"story_titre": "Consulter mon dossier", "note": 4, "commentaire": "CA2 à revoir"},
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps == {
        "id": 12,
        "session_id": 7,
        "story_titre": "Consulter mon dossier",
        "note": 4,
        "commentaire": "CA2 à revoir",
    }
    assert connexion.commits == 1
    insertion = [p for r, p in connexion.curseur.requetes if "INSERT INTO story_feedbacks" in r]
    assert insertion[0]["note"] == 4


def test_noter_session_inconnue_404(brancher) -> None:
    brancher([None])
    reponse = client.post("/workflows/99/feedback", json={"story_titre": "X", "note": 3})
    assert reponse.status_code == 404


@pytest.mark.parametrize("note", [0, 6])
def test_note_hors_bornes_422(brancher, note: int) -> None:
    brancher([(7,)])
    reponse = client.post("/workflows/7/feedback", json={"story_titre": "X", "note": note})
    assert reponse.status_code == 422


def test_titres_des_stories_de_la_session(brancher) -> None:
    brancher(
        [
            (7,),  # session existe
            [
                ("po", "recuperation_feature", "Ma feature"),
                ("assistant", "redaction", f"---\n{US_A}\n---"),
            ],
        ]
    )
    reponse = client.get("/workflows/7/stories")
    assert reponse.status_code == 200
    assert reponse.json() == ["Consulter mon dossier"]


def test_titres_vides_sans_redaction(brancher) -> None:
    brancher([(7,), [("po", "interview", "réponse")]])
    reponse = client.get("/workflows/7/stories")
    assert reponse.status_code == 200
    assert reponse.json() == []  # pas de 409 : l'écran masque le panneau


def test_telemetrie_calcule_les_trois_proxys(brancher) -> None:
    brancher(
        [
            (10,),  # sessions_total
            [("2026-06-29", 4), ("2026-07-06", 6)],  # sessions par semaine
            (5, 4.2, 4),  # stories notées, moyenne, notes >= 4
            (8, 2),  # validations, dont « Non »
        ]
    )
    reponse = client.get("/telemetrie")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["sessions_total"] == 10
    assert corps["actifs_hebdo"] == [
        {"semaine": "2026-06-29", "sessions": 4},
        {"semaine": "2026-07-06", "sessions": 6},
    ]
    assert corps["note_moyenne"] == 4.2
    assert corps["pourcentage_conservees"] == 0.8  # proxy v0 : note >= 4
    assert corps["taux_edition"] == 0.25  # proxy v0 : part des « Non »


def test_telemetrie_sans_donnees_pas_de_division_par_zero(brancher) -> None:
    brancher([(0,), [], (0, None, 0), (0, 0)])
    reponse = client.get("/telemetrie")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["note_moyenne"] is None
    assert corps["pourcentage_conservees"] is None
    assert corps["taux_edition"] is None
