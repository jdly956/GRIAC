"""Tests S2.9 : inventaire documents pour l'écran E4.3 — DB simulée."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app

client = TestClient(app)


class FauxCurseur:
    """File de résultats rejoués dans l'ordre des fetchone/fetchall du code."""

    def __init__(self, resultats: deque) -> None:
        self.resultats = resultats
        self.requetes: list[str] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append(requete)

    def fetchone(self):
        return self.resultats.popleft()

    def fetchall(self):
        return self.resultats.popleft()

    def __enter__(self) -> "FauxCurseur":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, resultats: list) -> None:
        self.curseur = FauxCurseur(deque(resultats))

    def cursor(self) -> FauxCurseur:
        return self.curseur


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> FausseConnexion:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        return connexion

    yield _brancher
    app.dependency_overrides.clear()


def test_liste_documents_expose_statuts_reference_doublon(brancher) -> None:
    brancher(
        [
            [
                ("pa/spec-v2.docx", "spec-v2.docx", "docx", "parse", True, False, "pa"),
                ("pa/spec-v1.docx", "spec-v1.docx", "docx", "parse", False, True, "pa"),
                ("divers/scan.pdf", "scan.pdf", "pdf", "ocr_requis", False, False, None),
            ]
        ]
    )
    reponse = client.get("/documents")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 3
    assert corps[0] == {
        "chemin": "pa/spec-v2.docx",
        "nom": "spec-v2.docx",
        "extension": "docx",
        "statut_parsing": "parse",
        "est_reference": True,
        "doublon": False,
        "projet_suggere": "pa",
    }
    assert corps[1]["doublon"] is True
    assert corps[2]["statut_parsing"] == "ocr_requis"
    assert corps[2]["projet_suggere"] is None


def test_stats_documents_calcule_la_couverture(brancher) -> None:
    # 10 documents dont 8 parsables : 6 parsés, 1 échec, 1 OCR requis ; 4 références.
    brancher([(10, 8, 6, 1, 1, 4)])
    reponse = client.get("/documents/stats")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] == 10
    assert corps["parsables"] == 8
    assert corps["parses"] == 6
    assert corps["echecs"] == 1
    assert corps["ocr_requis"] == 1
    assert corps["references"] == 4
    assert corps["couverture_parsing"] == 0.75


def test_stats_corpus_vide_couverture_pleine(brancher) -> None:
    # Aucun document parsable : pas de division par zéro, couverture affichée à 1.0.
    brancher([(2, 0, 0, 0, 0, 0)])
    reponse = client.get("/documents/stats")
    assert reponse.status_code == 200
    assert reponse.json()["couverture_parsing"] == 1.0
