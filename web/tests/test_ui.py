"""Tests E4.1 : écran de conversation — l'api est simulée (jamais appelée)."""

import pytest
from fastapi.testclient import TestClient

from sia_web import api_client
from sia_web.main import app

client = TestClient(app)

ETAT_SESSION = {
    "id": 1,
    "etape": "interview",
    "projet_id": None,
    "hypotheses": [
        {
            "id": 3,
            "texte": "Seuil 10 Mo [HYPOTHÈSE À VALIDER]",
            "origine": "modele",
            "statut": "en_attente",
        }
    ],
    "nb_en_attente": 1,
}
MESSAGES = [
    {"role": "po", "etape": "recuperation_feature", "contenu": "Ma feature"},
    {"role": "assistant", "etape": "interview", "contenu": "Q1 ? Q2 ?"},
]


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch):
    """Route les appels sortants vers des réponses canées ; enregistre les appels."""

    class FauxApi:
        def __init__(self) -> None:
            self.reponses: dict[tuple[str, str], tuple[int, object]] = {}
            self.appels: list[tuple[str, str, object]] = []

        def brancher(self, methode: str, chemin: str, statut: int, corps: object) -> None:
            self.reponses[(methode, chemin)] = (statut, corps)

        def __call__(self, methode: str, chemin: str, json: object = None):
            self.appels.append((methode, chemin, json))
            return self.reponses.get((methode, chemin), (404, {"detail": "non branché"}))

    faux = FauxApi()
    monkeypatch.setattr(api_client, "appeler", faux)
    return faux


def test_accueil_liste_les_projets(api) -> None:
    api.brancher(
        "GET",
        "/projects",
        200,
        [{"id": 1, "nom": "Téléservice X", "contexte": "Suivi", "nfrs": [], "dossiers": []}],
    )
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Téléservice X" in reponse.text
    assert "Ne collez pas de données personnelles" in reponse.text  # bandeau D15


def test_accueil_api_injoignable_reste_lisible(api) -> None:
    api.brancher("GET", "/projects", 599, {"detail": "API injoignable (http://x) : ConnectError"})
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "API injoignable" in reponse.text


def test_creation_de_session_redirige_vers_le_fil(api) -> None:
    api.brancher("POST", "/workflows", 201, {"id": 7})
    reponse = client.post(
        "/sessions", data={"feature": "Ma feature", "projet_id": "1"}, follow_redirects=False
    )
    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/sessions/7"
    assert api.appels[0][2] == {"feature": "Ma feature", "projet_id": 1}


def test_ecran_session_affiche_fil_etape_et_hypotheses(api) -> None:
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    reponse = client.get("/sessions/1")
    assert reponse.status_code == 200
    assert "1 — Interview de refinement" in reponse.text  # étape courante (A5)
    assert "Q1 ? Q2 ?" in reponse.text  # fil
    assert "Seuil 10 Mo" in reponse.text  # hypothèse en attente
    assert "Confirmer" in reponse.text and "Rejeter" in reponse.text  # décision individuelle A8
    assert "question documentaire libre" in reponse.text  # A2


def test_session_inconnue_page_erreur(api) -> None:
    api.brancher("GET", "/workflows/99", 404, {"detail": "Session 99 introuvable"})
    reponse = client.get("/sessions/99")
    assert reponse.status_code == 404
    assert "Session 99 introuvable" in reponse.text


def test_envoi_message_affiche_sources_et_avertissements(api) -> None:
    api.brancher(
        "POST",
        "/workflows/1/message",
        200,
        {
            "reponse": "Voici ma synthèse.",
            "etape": "interview",
            "sources": [{"document": "p/spec.docx", "nom": "spec.docx", "section": "Spec > CA"}],
            "hypotheses_ajoutees": ["Seuil 10 Mo [HYPOTHÈSE À VALIDER]"],
            "divergences": ["[DIVERGENCE] 15 j vs 30 j [Source : spec.docx]"],
            "avertissements": ["4 questions dans le lot — règle 1"],
        },
    )
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    reponse = client.post("/sessions/1/message", data={"message": "ma réponse"})
    assert reponse.status_code == 200
    assert "spec.docx — Spec &gt; CA" in reponse.text  # panneau sources A3
    assert "arbitrez (A9)" in reponse.text  # divergence
    assert "règle 1" in reponse.text  # avertissement


def test_validation_etape_oui_et_redirection(api) -> None:
    api.brancher("POST", "/workflows/1/avancer", 200, {})
    reponse = client.post(
        "/sessions/1/valider", data={"valide": "oui", "commentaire": ""}, follow_redirects=False
    )
    assert reponse.status_code == 303
    assert api.appels[0][2] == {"valide": True, "commentaire": ""}


def test_decision_hypothese_et_redirection(api) -> None:
    api.brancher("POST", "/workflows/1/hypotheses/3", 200, {})
    reponse = client.post(
        "/sessions/1/hypotheses/3", data={"statut": "confirmee"}, follow_redirects=False
    )
    assert reponse.status_code == 303
    assert api.appels[0][2] == {"statut": "confirmee"}


def test_export_proxifie(api, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_client,
        "telecharger",
        lambda chemin: (200, '"Summary","Issue Type","Description"\r\n', "text/csv; charset=utf-8"),
    )
    reponse = client.get("/sessions/1/export/csv")
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/csv")
    assert reponse.text.startswith('"Summary"')
