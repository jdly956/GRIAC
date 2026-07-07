"""Tests S3.11 : comptabilité tokens — registre conso_tokens (DB simulée)."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app


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

    def commit(self) -> None:
        pass


client = TestClient(app)


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> FausseConnexion:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        return connexion

    yield _brancher
    app.dependency_overrides.clear()


def test_conso_de_session(brancher) -> None:
    brancher([(3, 12_000, 4_500)])
    corps = client.get("/workflows/7/conso").json()
    assert corps == {"appels": 3, "tokens_entree": 12_000, "tokens_sortie": 4_500}


def test_conso_session_vide_sans_404(brancher) -> None:
    # Session inconnue ou sans appel : zéros — simple indication à l'écran.
    brancher([(0, 0, 0)])
    assert client.get("/workflows/99/conso").json()["appels"] == 0


def test_conso_globale_et_jauge_tpd(brancher, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALBERT_TPD_QUOTA", "1000")  # quota surchargeable sans code
    brancher(
        [
            (2_000, 900),  # totaux entrée/sortie
            (500,),  # conso du jour
            [("chat", 1_500, 900), ("embeddings", 500, 0)],
        ]
    )
    corps = client.get("/telemetrie/tokens").json()
    assert corps["total_entree"] == 2_000 and corps["total_sortie"] == 900
    assert corps["jour_total"] == 500
    assert corps["tpd_quota"] == 1_000
    assert corps["jour_part_tpd"] == 0.5  # la jauge : 500 / 1000
    assert [s["source"] for s in corps["par_source"]] == ["chat", "embeddings"]
