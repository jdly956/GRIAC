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


def test_prefixe_root_path_porte_liens_mais_pas_les_redirections(api) -> None:
    # Proxy à préfixe (code-server /proxy/8081/ sur pod Onyxia, 03/07/2026) :
    # les liens des templates portent le root_path (les corps HTML ne sont pas
    # réécrits par le proxy), mais les Location partent SANS préfixe — le proxy
    # les réécrit en pré-ajoutant /proxy/8081 (doublement constaté sinon).
    client_prefixe = TestClient(app, root_path="/proxy/8081")
    api.brancher("GET", "/projects", 200, [])
    reponse = client_prefixe.get("/")
    assert 'href="/proxy/8081/projets"' in reponse.text
    assert 'action="/proxy/8081/sessions"' in reponse.text
    api.brancher("POST", "/workflows", 201, {"id": 7})
    redirection = client_prefixe.post(
        "/sessions", data={"feature": "Ma feature"}, follow_redirects=False
    )
    assert redirection.headers["location"] == "/sessions/7"


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


# --- S2.10 : feedback par story + télémétrie (E4.4) ---


def test_panneau_de_notation_quand_des_stories_existent(api) -> None:
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    api.brancher("GET", "/workflows/1/stories", 200, ["Consulter mon dossier"])
    reponse = client.get("/sessions/1")
    assert reponse.status_code == 200
    assert "Noter les stories" in reponse.text
    assert "Consulter mon dossier" in reponse.text


def test_pas_de_panneau_sans_stories(api) -> None:
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    api.brancher("GET", "/workflows/1/stories", 200, [])
    reponse = client.get("/sessions/1")
    assert reponse.status_code == 200
    assert "Noter les stories" not in reponse.text


def test_notation_envoie_le_feedback_et_redirige(api) -> None:
    api.brancher("POST", "/workflows/1/feedback", 201, {"id": 12})
    reponse = client.post(
        "/sessions/1/feedback",
        data={"story_titre": "Consulter mon dossier", "note": "4", "commentaire": "CA2 à revoir"},
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    assert api.appels[0][2] == {
        "story_titre": "Consulter mon dossier",
        "note": 4,
        "commentaire": "CA2 à revoir",
    }


def test_ecran_telemetrie_affiche_les_proxys(api) -> None:
    api.brancher(
        "GET",
        "/telemetrie",
        200,
        {
            "sessions_total": 10,
            "actifs_hebdo": [{"semaine": "2026-06-29", "sessions": 4}],
            "stories_notees": 5,
            "note_moyenne": 4.2,
            "pourcentage_conservees": 0.8,
            "validations_total": 8,
            "taux_edition": 0.25,
        },
    )
    reponse = client.get("/telemetrie")
    assert reponse.status_code == 200
    assert "10 sessions au total" in reponse.text
    assert "80.0" in reponse.text  # % conservées
    assert "25.0" in reponse.text  # taux d'édition
    assert "2026-06-29" in reponse.text


def test_ecran_telemetrie_sans_donnees_reste_lisible(api) -> None:
    api.brancher(
        "GET",
        "/telemetrie",
        200,
        {
            "sessions_total": 0,
            "actifs_hebdo": [],
            "stories_notees": 0,
            "note_moyenne": None,
            "pourcentage_conservees": None,
            "validations_total": 0,
            "taux_edition": None,
        },
    )
    reponse = client.get("/telemetrie")
    assert reponse.status_code == 200
    assert "aucune story notée" in reponse.text
    assert "aucune validation" in reponse.text


# --- Écrans S2.9 : projets (E4.2) et « mes documents » (E4.3) ---

PROJET_DETAIL = {
    "id": 1,
    "nom": "Téléservice X",
    "contexte": "Suivi des demandes",
    "nfrs": [{"type": "performance", "formulation": "p95 < 1 s", "valeur_cible": "1 s"}],
    "dossiers": [
        {"dossier": "projet-alpha", "origine": "suggestion"},
        {"dossier": "dossier-manuel", "origine": "po"},
    ],
}
SUGGESTIONS = [
    {"dossier": "projet-alpha", "nb_documents": 3, "deja_associe": True},
    {"dossier": "projet-beta", "nb_documents": 2, "deja_associe": False},
]


def test_ecran_projets_liste_et_formulaire(api) -> None:
    api.brancher("GET", "/projects", 200, [PROJET_DETAIL])
    reponse = client.get("/projets")
    assert reponse.status_code == 200
    assert "Téléservice X" in reponse.text
    assert 'name="nfr_type_3"' in reponse.text  # 3 lignes NFR à la création
    assert "accessibilite_rgaa" in reponse.text  # les 7 types proposés


def test_creation_projet_construit_les_nfr(api) -> None:
    api.brancher("POST", "/projects", 201, {"id": 4, "nom": "P", "nfrs": [], "dossiers": []})
    reponse = client.post(
        "/projets",
        data={
            "nom": "P",
            "contexte": "ctx",
            "nfr_type_1": "performance",
            "nfr_formulation_1": "p95 < 1 s",
            "nfr_valeur_1": "1 s",
            "nfr_type_2": "rgpd",
            "nfr_formulation_2": "",  # formulation vide : la ligne est ignorée
        },
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/projets/4"
    assert api.appels[0][2] == {
        "nom": "P",
        "contexte": "ctx",
        "nfrs": [{"type": "performance", "formulation": "p95 < 1 s", "valeur_cible": "1 s"}],
        "dossiers": [],
    }


def test_creation_projet_nom_duplique_reste_sur_l_ecran(api) -> None:
    api.brancher("POST", "/projects", 409, {"detail": "Projet « P » déjà existant"})
    api.brancher("GET", "/projects", 200, [])
    reponse = client.post("/projets", data={"nom": "P"})
    assert reponse.status_code == 200
    assert "déjà existant" in reponse.text


def test_ecran_projet_detail_suggestions_et_ajout_manuel(api) -> None:
    api.brancher("GET", "/projects/1", 200, PROJET_DETAIL)
    api.brancher("GET", "/dossiers/suggestions", 200, SUGGESTIONS)
    reponse = client.get("/projets/1")
    assert reponse.status_code == 200
    assert 'value="projet-alpha" checked' in reponse.text  # associé : coché
    assert 'value="projet-beta" ' in reponse.text  # suggéré non associé : présent…
    assert 'value="projet-beta" checked' not in reponse.text  # … mais pas coché
    assert "dossier-manuel" in reponse.text and "(ajout manuel)" in reponse.text
    assert "elles ne valent pas association" in reponse.text  # A6


def test_association_dossiers_envoie_un_put_complet(api) -> None:
    api.brancher("GET", "/projects/1", 200, PROJET_DETAIL)
    api.brancher("GET", "/dossiers/suggestions", 200, SUGGESTIONS)
    api.brancher("PUT", "/projects/1", 200, PROJET_DETAIL)
    reponse = client.post(
        "/projets/1/dossiers",
        data={"dossiers": ["projet-alpha", "projet-beta"], "dossier_libre": "dossier-z"},
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    methode, chemin, corps = api.appels[-1]
    assert (methode, chemin) == ("PUT", "/projects/1")
    assert corps["nom"] == "Téléservice X"  # nom/contexte/nfrs préservés
    assert corps["nfrs"] == PROJET_DETAIL["nfrs"]
    assert corps["dossiers"] == [
        {"dossier": "projet-alpha", "origine": "suggestion"},  # origine existante conservée
        {"dossier": "projet-beta", "origine": "suggestion"},  # nouvelle suggestion cochée
        {"dossier": "dossier-z", "origine": "po"},  # ajout manuel
    ]


DOCUMENTS = [
    {
        "chemin": "projet-alpha/spec-v2.docx",
        "nom": "spec-v2.docx",
        "extension": "docx",
        "statut_parsing": "parse",
        "est_reference": True,
        "doublon": False,
        "projet_suggere": "projet-alpha",
    },
    {
        "chemin": "divers/scan.pdf",
        "nom": "scan.pdf",
        "extension": "pdf",
        "statut_parsing": "ocr_requis",
        "est_reference": False,
        "doublon": False,
        "projet_suggere": None,
    },
]


def _stats(couverture: float) -> dict:
    return {
        "total": 10,
        "parsables": 8,
        "parses": int(couverture * 8),
        "echecs": 1,
        "ocr_requis": 1,
        "references": 4,
        "couverture_parsing": couverture,
    }


def test_ecran_documents_alerte_couverture_faible(api) -> None:
    api.brancher("GET", "/documents", 200, DOCUMENTS)
    api.brancher("GET", "/documents/stats", 200, _stats(0.5))
    reponse = client.get("/documents")
    assert reponse.status_code == 200
    assert "Couverture documentaire faible" in reponse.text  # alerte A5
    assert "indexé" in reponse.text and "OCR requis" in reponse.text  # statuts libellés
    assert "✔ référence" in reponse.text


def test_ecran_documents_couverture_ok_sans_alerte(api) -> None:
    api.brancher("GET", "/documents", 200, DOCUMENTS)
    api.brancher("GET", "/documents/stats", 200, _stats(0.875))
    reponse = client.get("/documents")
    assert reponse.status_code == 200
    assert "Couverture documentaire faible" not in reponse.text


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
