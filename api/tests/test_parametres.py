"""Tests S3.12 : paramètres d'instance — modèle de chat changeable depuis l'UI."""

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


def test_sans_surcharge_le_defaut_est_actif(brancher) -> None:
    brancher([None])  # aucune ligne parametres
    corps = client.get("/parametres").json()
    assert corps["modele_chat"] is None
    assert corps["modele_actif"]  # le défaut (env/code) écrit les réponses
    assert "openweight-medium" in corps["modeles_proposes"]


def test_surcharge_lue(brancher) -> None:
    brancher([("openweight-large",)])
    corps = client.get("/parametres").json()
    assert corps["modele_chat"] == "openweight-large"
    assert corps["modele_actif"] == "openweight-large"


def test_changement_de_modele_upsert(brancher) -> None:
    connexion = brancher([])
    corps = client.put("/parametres/modele-chat", json={"modele": " openweight-large "}).json()
    assert corps["modele_actif"] == "openweight-large"  # espaces nettoyés
    requete, params = connexion.curseur.requetes[0]
    assert "ON CONFLICT (cle) DO UPDATE" in requete  # appliqué SANS relance
    assert params == {"cle": "modele_chat", "valeur": "openweight-large"}
    assert connexion.commits == 1


def test_retour_au_defaut(brancher) -> None:
    connexion = brancher([])
    corps = client.delete("/parametres/modele-chat").json()
    assert corps["modele_chat"] is None
    assert any("DELETE FROM parametres" in r for r, _ in connexion.curseur.requetes)
