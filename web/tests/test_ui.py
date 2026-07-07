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


def test_panneau_hypotheses_toujours_visible_dans_le_rail(api) -> None:
    # R2 (UX4/UX5, recale S3.7) : le registre vit dans le rail droit, OUVERT en
    # permanence — compteur et levées proposées (S2.13) restent sous les yeux.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)  # 1 en attente, sans proposition
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert '<details class="panneau-rail" open id="hypotheses">' in texte
    assert "Hypothèses à valider (1 en attente)" in texte
    avec_proposition = dict(
        ETAT_SESSION,
        hypotheses=[dict(ETAT_SESSION["hypotheses"][0], statut_propose="confirmee")],
    )
    api.brancher("GET", "/workflows/1", 200, avec_proposition)
    texte = client.get("/sessions/1").text
    assert "1 levée(s) proposée(s) à décider" in texte


def test_application_en_lot_des_levees_proposees(api) -> None:
    # S3.21 : dès qu'une levée proposée attend, le registre offre l'application
    # en lot (relue, confirmée par le PO) — les boutons individuels restent.
    avec_proposition = dict(
        ETAT_SESSION,
        hypotheses=[dict(ETAT_SESSION["hypotheses"][0], statut_propose="confirmee")],
    )
    api.brancher("GET", "/workflows/1", 200, avec_proposition)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert 'action="/sessions/1/hypotheses/appliquer-propositions"' in texte
    assert "Appliquer les 1 levée(s) proposée(s)" in texte
    assert 'action="/sessions/1/hypotheses/3"' in texte  # décision individuelle intacte

    api.brancher("POST", "/workflows/1/hypotheses/appliquer-propositions", 200, {})
    reponse = client.post("/sessions/1/hypotheses/appliquer-propositions", follow_redirects=False)
    assert reponse.status_code == 303
    assert ("POST", "/workflows/1/hypotheses/appliquer-propositions", None) in api.appels


def test_fil_complet_charge_dans_le_chat(api) -> None:
    # R2 (H2, recale S3.7) : le fil charge l'historique COMPLET — le chat a son
    # propre défilement, plus de bloc « voir les échanges précédents ».
    six_messages = [
        {"role": "po", "etape": "interview", "contenu": f"message numéro {i}"} for i in range(6)
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, six_messages)
    texte = client.get("/sessions/1").text
    assert "Voir les" not in texte
    for i in range(6):
        assert f"message numéro {i}" in texte  # tous les messages sont dans le fil


def test_reponse_du_post_rejoint_le_bas_du_fil(api) -> None:
    # R2 (UX6/H3, recale S3.7) : après un envoi, la réponse est le DERNIER
    # message du fil (chat classique, ancre #dernier-echange) — le panneau
    # « Dernière réponse » séparé a disparu.
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
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
    assert "<strong>Voici la story</strong>" in texte  # rendue markdown
    assert texte.index("Q1 ? Q2 ?") < texte.index("Voici la story")  # au BAS du fil
    # Stack réelle : la réponse est déjà persistée dans le fil (S3.9) — le bloc
    # d'appoint est sauté, pas de doublon.
    api.brancher(
        "GET",
        "/workflows/1/messages",
        200,
        MESSAGES + [{"role": "assistant", "etape": "interview", "contenu": "**Voici la story**"}],
    )
    texte = client.post("/sessions/1/message", data={"message": "go"}).text
    assert texte.count("Voici la story") == 1  # une seule occurrence


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
    # S3.8 (recalée R3/H7, validée PO 07/07) : htmx est servi par l'app (pas de
    # CDN) et les formulaires longs POSTent en fragments ciblés vers le fil
    # (anti double-envoi + indicateur) — POST classiques intacts sans JavaScript.
    statique = client.get("/static/htmx.min.js")
    assert statique.status_code == 200
    assert statique.text.startswith("var htmx=")
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, etape="redaction"))
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert 'src="/static/htmx.min.js"' in texte
    assert texte.count('hx-post="/sessions/1/') == 3  # message, story suivante, valider
    assert texte.count('hx-target="#fil"') == 3
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


DOCS_STATS = {
    "total": 1,
    "parsables": 1,
    "parses": 1,
    "echecs": 0,
    "ocr_requis": 0,
    "references": 1,
    "couverture_parsing": 1.0,
}


def test_depot_et_indexation_depuis_mes_documents(api, monkeypatch: pytest.MonkeyPatch) -> None:
    # S3.10 : formulaire de dépôt + bouton « Indexer maintenant » (manuel) +
    # suivi des runs nœud par nœud, rafraîchi tant qu'un run tourne.
    api.brancher("GET", "/documents", 200, [])
    api.brancher("GET", "/documents/stats", 200, DOCS_STATS)
    api.brancher(
        "GET",
        "/ingestion/runs",
        200,
        [
            {
                "id": 2,
                "statut": "en_cours",
                "corpus": "corpus",
                "rapport": {"scan": "ok"},
                "demarre_le": "2026-07-06 21:10",
                "termine_le": None,
            }
        ],
    )
    api.brancher("GET", "/documents/dossiers", 200, ["projet-alpha"])
    texte = client.get("/documents").text
    assert "Déposer un document" in texte
    assert "Indexation en cours…" in texte  # bouton désactivé pendant un run
    assert 'http-equiv="refresh"' in texte  # suivi en direct
    assert "scan : ok" in texte
    # S3.18 : dossier obligatoire, dossiers existants proposés en datalist.
    assert 'name="dossier"' in texte and "required" in texte
    assert '<option value="projet-alpha">' in texte

    envois: list[tuple[str, str, dict | None]] = []
    monkeypatch.setattr(
        api_client,
        "envoyer_fichier",
        lambda chemin, nom, contenu, ct, donnees=None: (
            envois.append((chemin, nom, donnees)) or (201, {})
        ),
    )
    reponse = client.post(
        "/documents/upload",
        files={"fichier": ("spec.docx", b"contenu", "application/msword")},
        data={"dossier": "projet-alpha"},
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    # Le dossier saisi est transmis à l'api avec le fichier (S3.18).
    assert envois == [("/documents/upload", "spec.docx", {"dossier": "projet-alpha"})]

    api.brancher("POST", "/ingestion/lancer", 202, {"id": 3})
    assert client.post("/documents/indexer", follow_redirects=False).status_code == 303
    assert any(a[:2] == ("POST", "/ingestion/lancer") for a in api.appels)


def test_extrait_anormalement_long_tronque_a_l_affichage(api) -> None:
    # S3.20 (session 12) : un extrait de 940k chars (chunk-tableau xlsx) rendait
    # la page inutilisable — l'affichage est borné, la mention l'explique.
    messages = [
        {
            "role": "assistant",
            "etape": "interview",
            "contenu": "Réponse",
            "sources": [{"nom": "gros.xlsx", "section": "Feuille1", "extrait": "| x |" * 3000}],
            "avertissements": [],
            "divergences": [],
        }
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, messages)
    texte = client.get("/sessions/1").text
    assert "affichage tronqué à 2 000 caractères sur 15000" in texte
    assert texte.count("| x |") < 1000  # la page ne porte plus l'extrait entier


def test_traces_du_fil_avec_extrait_exact(api) -> None:
    # S3.9 : au rechargement, chaque message assistant garde ses sources —
    # l'extrait exact du chunk est consultable (la promesse A3).
    messages = [
        {
            "role": "assistant",
            "etape": "interview",
            "contenu": "Réponse sourcée",
            "sources": [
                {"nom": "spec_v2.docx", "section": "Spec > CA", "extrait": "délai de 30 jours"}
            ],
            "avertissements": ["Budget dépassé"],
            "divergences": [],
        }
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, messages)
    texte = client.get("/sessions/1").text
    assert "Sources mobilisées (1)" in texte
    assert "extrait exact" in texte and "délai de 30 jours" in texte
    assert "Budget dépassé" in texte


def test_edition_et_gestion_de_session(api) -> None:
    # S3.13 : panneau d'édition (version éditée gagnante à l'export), copie,
    # renommage et archivage (masque sans détruire).
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, [])
    api.brancher(
        "GET",
        "/workflows/1/stories/contenus",
        200,
        [{"titre": "Consulter mon dossier", "contenu": "**US — …**", "editee": True}],
    )
    texte = client.get("/sessions/1").text
    assert "Stories produites (1)" in texte  # R2 : le panneau du rail
    assert "éditée — cette version part à l'export" in texte
    assert "navigator.clipboard.writeText" in texte  # bouton copier (dégradé sans JS : textarea)
    assert "Gérer la session" in texte  # R2 : dans la barre de session

    api.brancher("PUT", "/workflows/1/stories/edition", 200, {})
    reponse = client.post(
        "/sessions/1/stories/edition",
        data={"titre": "Consulter mon dossier", "contenu": "édité"},
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    appel = next(a for a in api.appels if a[0] == "PUT" and "edition" in a[1])
    assert appel[2] == {"titre": "Consulter mon dossier", "contenu": "édité"}

    api.brancher("PATCH", "/workflows/1", 200, {})
    archive = client.post("/sessions/1/gerer", data={"archiver": "1"}, follow_redirects=False)
    assert archive.headers["location"] == "/"  # retour à l'accueil après archivage
    patch = next(a for a in api.appels if a[0] == "PATCH")
    assert patch[2] == {"archivee": True}


def test_fiche_document_affiche_le_traitement(api) -> None:
    # S3.14 : depuis « Mes documents », chaque document a sa fiche — parsing,
    # dérivé markdown rendu, chunks avec état d'embedding.
    api.brancher(
        "GET",
        "/documents/1",
        200,
        {
            "id": 1,
            "chemin": "pa/spec-v2.docx",
            "nom": "spec-v2.docx",
            "extension": "docx",
            "taille_octets": 12345,
            "sha256": "abc123def456ghij",
            "statut_parsing": "parse",
            "erreur_parsing": None,
            "date_parsing": "2026-07-06 22:00",
            "chemin_derive": "derived/md/abc.md",
            "derive_apercu": "# Titre parsé\n\n| A | B |\n|---|---|\n| 1 | 2 |",
            "derive_tronque": False,
            "est_reference": True,
            "doublon_de": None,
            "projet_suggere": "pa",
            "version_no": 2,
            "groupe_version": "spec",
            "chunks": [
                {
                    "ordinal": 0,
                    "section": "Spec > Exigences",
                    "nb_tokens": 640,
                    "contenu": "contenu exact du chunk",
                    "embarque": True,
                }
            ],
            "nb_chunks": 1,
            "nb_embarques": 1,
        },
    )
    texte = client.get("/documents/1").text
    assert "Voir le résultat du parsing" in texte
    assert "<table>" in texte  # le dérivé markdown est rendu
    assert "Chunks (E1, nœud D) — 1, dont 1 vectorisé(s)" in texte
    assert "Spec &gt; Exigences" in texte or "Spec > Exigences" in texte
    assert "✅ vectorisé" in texte
    assert "contenu exact du chunk" in texte


FICHE_MINIMALE = {
    "id": 1,
    "chemin": "pa/spec-v2.docx",
    "nom": "spec-v2.docx",
    "extension": "docx",
    "taille_octets": 12345,
    "sha256": "abc123def456ghij",
    "statut_parsing": "parse",
    "erreur_parsing": None,
    "date_parsing": None,
    "chemin_derive": None,
    "derive_apercu": None,
    "derive_tronque": False,
    "est_reference": False,
    "doublon_de": None,
    "projet_suggere": None,
    "version_no": None,
    "groupe_version": None,
    "chunks": [],
    "nb_chunks": 0,
    "nb_embarques": 0,
}


def test_fiche_document_actions_telecharger_et_supprimer(api) -> None:
    # S3.17 : la fiche porte le téléchargement de l'original et la suppression
    # (confirmée — l'action est définitive).
    api.brancher("GET", "/documents/1", 200, FICHE_MINIMALE)
    texte = client.get("/documents/1").text
    assert 'href="/documents/1/original"' in texte
    assert 'action="/documents/1/supprimer"' in texte
    assert "confirm(" in texte  # garde-fou navigateur avant une action définitive


def test_suppression_document_redirige_vers_l_inventaire(api) -> None:
    api.brancher("DELETE", "/documents/1", 204, {})
    reponse = client.post("/documents/1/supprimer", follow_redirects=False)
    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/documents"
    assert ("DELETE", "/documents/1", None) in api.appels


def test_telechargement_original_proxifie_en_binaire(monkeypatch: pytest.MonkeyPatch) -> None:
    # S3.17 : proxy BINAIRE (un .docx passé par .text serait corrompu) ; le
    # Content-Disposition de l'api (nom du fichier) est propagé au navigateur.
    monkeypatch.setattr(
        api_client,
        "telecharger_binaire",
        lambda chemin: (
            200,
            b"\x50\x4b\x03\x04octets docx",
            "application/octet-stream",
            'attachment; filename="spec-v2.docx"',
        ),
    )
    reponse = client.get("/documents/1/original")
    assert reponse.status_code == 200
    assert reponse.content == b"\x50\x4b\x03\x04octets docx"
    assert reponse.headers["content-disposition"] == 'attachment; filename="spec-v2.docx"'


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


def test_panneau_stories_du_rail_porte_la_notation(api) -> None:
    # R2 (H11) : la notation E4.4 vit dans le panneau « Stories produites » du
    # rail — repli sur les seuls titres si l'endpoint contenus manque.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    api.brancher("GET", "/workflows/1/stories", 200, ["Consulter mon dossier"])
    reponse = client.get("/sessions/1")
    assert reponse.status_code == 200
    assert "Stories produites (1)" in reponse.text
    assert "Consulter mon dossier" in reponse.text
    assert 'aria-label="Note de « Consulter mon dossier »"' in reponse.text


def test_pas_de_panneau_sans_stories(api) -> None:
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    api.brancher("GET", "/workflows/1/stories", 200, [])
    reponse = client.get("/sessions/1")
    assert reponse.status_code == 200
    assert "Stories produites" not in reponse.text


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


# --- R1 : socle DSFR & navigation (refonte UX/UI, arbitrages UX9/UX11/UX13) ---


def test_socle_dsfr_header_notice_et_ressources(api) -> None:
    # R1 : en-tête DSFR officiel + notice D15 discrète (l'obligation d'affichage
    # demeure — plus d'alerte pleine largeur) ; CSS ET JS DSFR chargés (H15).
    api.brancher("GET", "/projects", 200, [])
    texte = client.get("/").text
    assert 'class="fr-header"' in texte and 'class="fr-nav"' in texte
    assert 'class="fr-notice fr-notice--info"' in texte
    assert "Ne collez pas de données personnelles" in texte  # D15 tenu
    assert "fr-alert fr-alert--warning" not in texte  # l'ancienne alerte a disparu
    assert "dsfr.min.css" in texte and "dsfr.module.min.js" in texte


def test_navigation_entree_active_par_ecran(api) -> None:
    # R1 : l'entrée active porte aria-current — le PO sait toujours où il est.
    api.brancher("GET", "/projects", 200, [])
    accueil = client.get("/").text
    assert '<a class="fr-nav__link" href="/" aria-current="true">Sessions</a>' in accueil
    api.brancher("GET", "/documents", 200, [])
    api.brancher("GET", "/documents/stats", 200, DOCS_STATS)
    documents = client.get("/documents").text
    assert 'href="/documents" aria-current="true">Mes documents</a>' in documents
    assert 'href="/" aria-current="true"' not in documents  # une seule entrée active


def test_fil_ariane_sur_les_fiches(api) -> None:
    # R1 : fil d'Ariane DSFR sur les sous-pages (fiche document, fiche projet).
    api.brancher("GET", "/documents/1", 200, FICHE_MINIMALE)
    texte = client.get("/documents/1").text
    assert 'class="fr-breadcrumb"' in texte
    assert 'href="/documents">Mes documents</a>' in texte
    api.brancher("GET", "/projects/1", 200, PROJET_DETAIL)
    api.brancher("GET", "/dossiers/suggestions", 200, SUGGESTIONS)
    assert 'class="fr-breadcrumb"' in client.get("/projets/1").text


# --- R2 : écran session — barre, chat, rail (refonte UX/UI, vague 1) ---


def test_barre_session_stepper_et_actions(api) -> None:
    # R2 : la barre de session porte le stepper d'étape (A5/H8), les exports
    # (H13) et la gestion de session — plus de blocs en bas de page.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert "Étape 2 sur 6" in texte  # interview = 2e étape du workflow 0→5
    assert 'data-fr-current-step="2" data-fr-steps="6"' in texte
    assert 'href="/sessions/1/export/csv"' in texte  # exports dans la barre (H13)
    assert "Gérer la session" in texte


def test_rail_sources_de_la_derniere_reponse(api) -> None:
    # R2 (H6) : le rail montre les sources du dernier message assistant tracé
    # (S3.9) — l'historique complet reste dans le fil.
    messages = MESSAGES + [
        {
            "role": "assistant",
            "etape": "interview",
            "contenu": "Réponse sourcée",
            "sources": [{"nom": "spec.docx", "section": "Spec > CA", "extrait": "30 jours"}],
        }
    ]
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, hypotheses=[], nb_en_attente=0))
    api.brancher("GET", "/workflows/1/messages", 200, messages)
    texte = client.get("/sessions/1").text
    assert "Sources de la dernière réponse (1)" in texte
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)  # aucun message sourcé
    texte = client.get("/sessions/1").text
    assert "Sources de la dernière réponse (0)" in texte
    assert "Aucune source mobilisée sur la dernière réponse" in texte


# --- R3 : dynamisme htmx en fragments ciblés (H7, validée PO 07/07) ---

REPONSE_MOTEUR = {
    "reponse": "**Frag**",
    "etape": "interview",
    "sources": [{"nom": "spec.docx", "section": "Spec > CA", "extrait": "30 jours"}],
    "hypotheses_ajoutees": ["Seuil 10 Mo [HYPOTHÈSE À VALIDER]"],
    "levees_proposees": [],
    "divergences": [],
    "avertissements": [],
}


def test_envoi_htmx_renvoie_fragment_bulles_et_oob(api) -> None:
    # R3 : un POST htmx reçoit un FRAGMENT — bulles PO + assistant à ajouter au
    # fil, panneaux du rail / stepper / conso en out-of-band. Pas de page.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("POST", "/workflows/1/message", 200, REPONSE_MOTEUR)
    reponse = client.post(
        "/sessions/1/message", data={"message": "ma question"}, headers={"HX-Request": "true"}
    )
    texte = reponse.text
    assert "fr-header" not in texte  # un fragment, pas la page complète
    assert "ma question" in texte  # bulle PO ajoutée au fil
    assert "<strong>Frag</strong>" in texte  # bulle assistant rendue markdown
    assert 'id="dernier-echange"' in texte
    assert "1 hypothèse(s) ajoutée(s)" in texte  # signal A8 dans la bulle
    assert texte.count('hx-swap-oob="true"') == 5  # stepper, conso, 3 panneaux du rail
    assert 'id="stepper"' in texte and 'id="sources-rail"' in texte
    assert "Sources de la dernière réponse (1)" in texte


def test_envoi_sans_javascript_reste_pleine_page(api) -> None:
    # H14 : le même POST sans en-tête HX-Request rend la page complète.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("GET", "/workflows/1/messages", 200, MESSAGES)
    api.brancher("POST", "/workflows/1/message", 200, REPONSE_MOTEUR)
    texte = client.post("/sessions/1/message", data={"message": "go"}).text
    assert "fr-header" in texte  # page complète (repli)


def test_erreur_moteur_en_fragment_sans_oob(api) -> None:
    # R3 : sur erreur, le fragment ne porte que l'alerte — pas d'out-of-band
    # (l'écran garde l'état du dernier succès), pas de bulle PO orpheline.
    api.brancher("GET", "/workflows/1", 200, ETAT_SESSION)
    api.brancher("POST", "/workflows/1/message", 429, {"detail": "quota Albert atteint"})
    reponse = client.post(
        "/sessions/1/message", data={"message": "go"}, headers={"HX-Request": "true"}
    )
    texte = reponse.text
    assert "quota Albert atteint" in texte and "fr-alert--error" in texte
    assert "hx-swap-oob" not in texte
    assert 'id="dernier-echange"' not in texte


def test_valider_htmx_fragment_avec_stepper_a_jour(api) -> None:
    # R3 : la validation d'étape en htmx renvoie la décision (bulle PO), la
    # réponse du moteur et le stepper OOB — l'étape affichée suit (A5).
    api.brancher("POST", "/workflows/1/avancer", 200, {})
    api.brancher(
        "POST",
        "/workflows/1/message",
        200,
        dict(REPONSE_MOTEUR, reponse="Étape suivante…", etape="stories_candidates"),
    )
    api.brancher("GET", "/workflows/1", 200, dict(ETAT_SESSION, etape="stories_candidates"))
    reponse = client.post(
        "/sessions/1/valider",
        data={"valide": "oui", "commentaire": ""},
        headers={"HX-Request": "true"},
    )
    texte = reponse.text
    assert "Étape validée (Oui)" in texte  # la décision PO apparaît dans le fil
    assert 'id="stepper"' in texte and 'hx-swap-oob="true"' in texte
    assert 'data-fr-current-step="3"' in texte  # stories_candidates = 3e étape


# --- R4 : sélection en masse des hypothèses (H5, arbitrage UX1) ---


def test_selection_en_masse_des_hypotheses(api) -> None:
    # R4 : cases rattachées au formulaire de lot par l'attribut form (pas
    # d'imbrication de formulaires) ; le statut envoyé est celui du bouton
    # cliqué par le PO (A8) ; seules les en_attente sont cochables.
    etat = dict(
        ETAT_SESSION,
        hypotheses=[
            dict(ETAT_SESSION["hypotheses"][0]),
            {
                "id": 4,
                "texte": "SSO requis [HYPOTHÈSE À VALIDER]",
                "origine": "modele",
                "statut": "en_attente",
            },
            {"id": 5, "texte": "Déjà levée", "origine": "po", "statut": "confirmee"},
        ],
        nb_en_attente=2,
    )
    api.brancher("GET", "/workflows/1", 200, etat)
    api.brancher("GET", "/workflows/1/messages", 200, [])
    texte = client.get("/sessions/1").text
    assert texte.count('form="form-lot-hypotheses"') == 2  # 2 en_attente cochables, pas la levée
    assert "Confirmer la sélection" in texte and "Rejeter la sélection" in texte
    assert "Tout sélectionner" in texte

    api.brancher("POST", "/workflows/1/hypotheses/decider-lot", 200, {})
    reponse = client.post(
        "/sessions/1/hypotheses/decider-lot",
        data={"statut": "rejetee", "hypothese_ids": ["3", "4"]},
        follow_redirects=False,
    )
    assert reponse.status_code == 303
    appel = next(a for a in api.appels if "decider-lot" in a[1])
    assert appel[2] == {"ids": [3, 4], "statut": "rejetee"}


def test_lot_sans_selection_ne_touche_pas_l_api(api) -> None:
    # A8 : aucune case cochée → aucun appel api — jamais de décision implicite.
    reponse = client.post(
        "/sessions/1/hypotheses/decider-lot", data={"statut": "confirmee"}, follow_redirects=False
    )
    assert reponse.status_code == 303
    assert not any("decider-lot" in chemin for _, chemin, _ in api.appels)
