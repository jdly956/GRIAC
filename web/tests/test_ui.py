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


def test_accueil_liste_les_sessions_en_cours(api) -> None:
    api.brancher("GET", "/projects", 200, [])
    api.brancher(
        "GET",
        "/workflows",
        200,
        [{"id": 7, "etape": "interview", "projet_id": 1, "apercu_feature": "Feature : connexion"}],
    )
    reponse = client.get("/")
    assert 'href="/sessions/7"' in reponse.text  # la session se RETROUVE depuis l'accueil
    assert "1 — Interview de refinement" in reponse.text
    assert "Feature : connexion" in reponse.text


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


def test_registre_replie_sauf_levee_proposee_a_decider(api) -> None:
    # S3.7 : le registre est replié par défaut ; il ne se déplie tout seul que
    # si une levée proposée (S2.13) attend la décision du PO.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)  # 1 en attente, sans proposition
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert '<details class="panneau" >' in texte and "Hypothèses à valider (1 en attente)" in texte
    avec_proposition = dict(
        ETAT_SESSION,
        hypotheses=[dict(ETAT_SESSION["hypotheses"][0], statut_propose="confirmee")],
    )
    api.brancher("GET", "/workflows/1", 200, avec_proposition)
    texte = client.get("/sessions/1").text
    assert '<details class="panneau" open>' in texte
    assert "1 levée(s) proposée(s) à décider" in texte


def test_fil_replie_sauf_derniers_echanges(api) -> None:
    # S3.7 : la page ne s'allonge plus indéfiniment — seuls les 4 derniers
    # messages restent dépliés, les précédents vivent dans un bloc repliable.
    six_messages = [
        {"role": "po", "etape": "interview", "contenu": f"message numéro {i}"} for i in range(6)
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, six_messages)
    texte = client.get("/sessions/1").text
    assert "Voir les 2 échanges précédents" in texte
    assert "message numéro 5" in texte  # les récents sont toujours là
    api.brancher("GET", "/workflows/1/messages", 200, six_messages[:2])
    assert "Voir les" not in client.get("/sessions/1").text  # ≤ 4 messages : rien à replier


def test_derniere_reponse_affichee_en_haut_apres_envoi(api) -> None:
    # S3.7 : après un envoi, la réponse (rendue) et sa traçabilité sont en haut
    # de page — plus besoin de scroller jusqu'au fil.
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, [])
    api.brancher(
        "POST",
        "/workflows/1/message",
        200,
        {
            "reponse": "**Voici la story**",
            "etape": "interview",
            "sources": [],
            "hypotheses_ajoutees": [],
            "levees_proposees": [],
            "divergences": [],
            "avertissements": [],
        },
    )
    texte = client.post("/sessions/1/message", data={"message": "go"}).text
    assert 'id="dernier-echange"' in texte
    assert "<strong>Voici la story</strong>" in texte  # rendue markdown, en haut


def test_messages_assistant_rendus_en_markdown(api) -> None:
    # S3.6 : le PO lisait les tableaux Gherkin en pipes bruts (sessions 9/11).
    messages = [
        {"role": "po", "etape": "interview", "contenu": "**pas rendu** côté PO"},
        {
            "role": "assistant",
            "etape": "redaction",
            "contenu": "**US — Titre**\n\n| # | Étant donné que… | Lorsque… | Alors… |\n"
            "|---|---|---|---|\n| CA1 | contexte | action | résultat |",
        },
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, messages)
    reponse = client.get("/sessions/1")
    assert "<table>" in reponse.text and "<strong>US — Titre</strong>" in reponse.text
    assert "| CA1 |" not in reponse.text  # plus de pipes bruts côté assistant
    assert "**pas rendu** côté PO" in reponse.text  # le message PO reste du texte brut


def test_html_du_moteur_echappe_jamais_interprete(api) -> None:
    # Le contenu vient du LLM : tout HTML source est échappé (html=False).
    messages = [
        {"role": "assistant", "etape": "interview", "contenu": "<script>alert(1)</script> ok"}
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, messages)
    reponse = client.get("/sessions/1")
    assert "<script>alert(1)</script>" not in reponse.text
    assert "&lt;script&gt;" in reponse.text


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


def test_levee_proposee_affichee_sans_lever(api) -> None:
    # Rapprochement interview↔registre (S2.13) : la proposition du moteur
    # s'affiche à côté des boutons — la décision individuelle reste au PO (A8).
    etat = {
        "id": 1,
        "etape": "interview",
        "projet_id": None,
        "hypotheses": [
            {
                "id": 3,
                "texte": "Seuil 10 Mo [HYPOTHÈSE À VALIDER]",
                "origine": "modele",
                "statut": "en_attente",
                "statut_propose": "confirmee",
                "justification_proposee": "le PO a fixé 10 Mo",
            }
        ],
        "nb_en_attente": 1,
    }
    api.brancher("GET", "/workflows/1", 200, etat)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    reponse = client.get("/sessions/1")
    assert "Levée proposée" in reponse.text
    assert "le PO a fixé 10 Mo" in reponse.text
    assert "c'est vous qui décidez (A8)" in reponse.text
    assert "Confirmer" in reponse.text and "Rejeter" in reponse.text  # boutons intacts


def test_bouton_story_suivante_aux_etapes_de_production(api) -> None:
    # Arbitrage S3.2 : une story = rédaction + DoR — le bouton itère sans
    # toucher la machine à états ; absent hors étapes de production.
    etat = dict(ETAT_SESSION, etape="redaction", hypotheses=[], nb_en_attente=0)
    api.brancher("GET", "/workflows/1", 200, etat)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    reponse = client.get("/sessions/1")
    assert "Story suivante" in reponse.text
    assert "sans changer d'étape" in reponse.text
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)  # étape interview
    assert "Story suivante" not in client.get("/sessions/1").text


def test_story_suivante_appelle_le_moteur_sans_avancer(api) -> None:
    etat = dict(ETAT_SESSION, etape="redaction", hypotheses=[], nb_en_attente=0)
    api.brancher("GET", "/workflows/1", 200, etat)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    api.brancher(
        "POST",
        "/workflows/1/message",
        200,
        {
            "reponse": "US suivante…",
            "etape": "redaction",
            "sources": [],
            "hypotheses_ajoutees": [],
            "levees_proposees": [],
            "divergences": [],
            "avertissements": [],
        },
    )
    assert client.post("/sessions/1/story-suivante").status_code == 200
    chemins = [(methode, chemin) for methode, chemin, _ in api.appels]
    assert ("POST", "/workflows/1/message") in chemins
    assert not any(chemin.endswith("/avancer") for _, chemin in chemins)  # A5 : état intact
    corps = next(j for m, c, j in api.appels if (m, c) == ("POST", "/workflows/1/message"))
    assert "STORY SUIVANTE" in corps["message"]


def test_htmx_vendore_et_branche_en_progressive_enhancement(api) -> None:
    # S3.8 : htmx est servi par l'app (pas de CDN) et les formulaires longs
    # portent hx-boost + anti double-envoi + indicateur — tout en restant des
    # POST classiques sans JavaScript.
    statique = client.get("/static/htmx.min.js")
    assert statique.status_code == 200
    assert statique.text.startswith("var htmx=")
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, etape="redaction"))
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert 'src="/static/htmx.min.js"' in texte
    assert texte.count('hx-boost="true"') == 3  # message, story suivante, valider
    assert texte.count('hx-disabled-elt="find button"') == 3
    assert "Génération en cours" in texte
    assert 'action="/sessions/1/message"' in texte  # le repli sans JS demeure


def test_htmx_prefixe_par_le_root_path(api) -> None:
    client_prefixe = TestClient(app, root_path="/proxy/8081")
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client_prefixe.get("/sessions/1").text
    assert 'src="/proxy/8081/static/htmx.min.js"' in texte


def test_conso_de_session_affichee(api) -> None:
    # S3.11 : la conso s'affiche sous le titre — simple indication, l'écran
    # reste servi si l'endpoint est absent (défaut 404 des autres tests).
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, [])
    api.brancher(
        "GET",
        "/workflows/1/conso",
        200,
        {"appels": 3, "tokens_entree": 12000, "tokens_sortie": 4500},
    )
    texte = client.get("/sessions/1").text
    assert "Consommation de la session : 3 appel(s)" in texte
    assert "12 000 tokens entrée" in texte


def test_jauge_tokens_en_telemetrie(api) -> None:
    api.brancher(
        "GET",
        "/telemetrie",
        200,
        {
            "sessions_total": 1,
            "actifs_hebdo": [],
            "stories_notees": 0,
            "note_moyenne": None,
            "pourcentage_conservees": None,
            "validations_total": 0,
            "taux_edition": None,
        },
    )
    api.brancher(
        "GET",
        "/telemetrie/tokens",
        200,
        {
            "total_entree": 200000,
            "total_sortie": 50000,
            "jour_total": 123000,
            "tpd_quota": 2460000,
            "jour_part_tpd": 0.05,
            "par_source": [{"source": "chat", "tokens_entree": 150000, "tokens_sortie": 50000}],
        },
    )
    texte = client.get("/telemetrie").text
    assert "123 000 tokens" in texte
    assert "5.0 % du quota quotidien" in texte
    assert "Chat (sessions)" in texte


def test_ecran_parametres_et_changement_de_modele(api) -> None:
    # S3.12 : réglage global instance — modèle actif affiché, changement PUT,
    # champ libre prioritaire sur le select, retour au défaut en DELETE.
    api.brancher(
        "GET",
        "/parametres",
        200,
        {
            "modele_chat": None,
            "modele_actif": "openweight-medium",
            "modeles_proposes": ["openweight-medium", "openweight-large"],
        },
    )
    texte = client.get("/parametres").text
    assert "openweight-medium" in texte and "défaut de l'instance" in texte
    api.brancher("PUT", "/parametres/modele-chat", 200, {})
    reponse = client.post(
        "/parametres/modele",
        data={"modele": "openweight-medium", "modele_libre": "mistral-medium"},
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    appel = next(a for a in api.appels if a[0] == "PUT")
    assert appel[2] == {"modele": "mistral-medium"}  # le champ libre prime
    api.brancher("DELETE", "/parametres/modele-chat", 200, {})
    client.post("/parametres/modele-defaut", follow_redirects=False)
    assert any(a[0] == "DELETE" for a in api.appels)


def test_modele_actif_affiche_sur_la_session(api) -> None:
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, [])
    api.brancher(
        "GET",
        "/parametres",
        200,
        {
            "modele_chat": "openweight-large",
            "modele_actif": "openweight-large",
            "modeles_proposes": [],
        },
    )
    assert "Modèle : <strong>openweight-large</strong>" in client.get("/sessions/1").text


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


def test_validation_etape_oui_declenche_le_moteur(api) -> None:
    # Règle 5 bouclée (bug constaté 06/07/2026) : le bouton « Oui » ne se
    # contente plus d'avancer l'état — la décision est transmise au moteur,
    # qui produit l'entrée de l'étape suivante dans le même aller-retour.
    api.brancher("POST", "/workflows/1/avancer", 200, {})
    api.brancher(
        "POST",
        "/workflows/1/message",
        200,
        {"reponse": "Étape suivante…", "etape": "interview", "sources": [], "avertissements": []},
    )
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    reponse = client.post("/sessions/1/valider", data={"valide": "oui", "commentaire": ""})
    assert reponse.status_code == 200
    assert api.appels[0][2] == {"valide": True, "commentaire": ""}
    methode, chemin, corps = api.appels[1]
    assert (methode, chemin) == ("POST", "/workflows/1/message")
    assert "Étape validée (Oui)" in corps["message"]


def test_validation_etape_non_transmet_le_commentaire_au_moteur(api) -> None:
    api.brancher("POST", "/workflows/1/avancer", 200, {})
    api.brancher(
        "POST",
        "/workflows/1/message",
        200,
        {"reponse": "J'itère…", "etape": "interview", "sources": [], "avertissements": []},
    )
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    reponse = client.post(
        "/sessions/1/valider", data={"valide": "non", "commentaire": "revoir le CA2"}
    )
    assert reponse.status_code == 200
    assert api.appels[0][2] == {"valide": False, "commentaire": "revoir le CA2"}
    assert "revoir le CA2" in api.appels[1][2]["message"]


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
