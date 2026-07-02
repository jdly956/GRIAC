"""Tests du web (CA3 de S1.2) : /health et présence du bandeau D15 — sans Docker."""

from fastapi.testclient import TestClient

from sia_web.main import app

client = TestClient(app)


def test_health_repond_200() -> None:
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


def test_index_affiche_le_bandeau_donnees_personnelles() -> None:
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Ne collez pas de données personnelles" in reponse.text
