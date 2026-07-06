"""Tests E3.1 : machine à états (pur) + API sessions/hypothèses (DB simulée)."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app
from sia_api.workflow import (
    ETAPES,
    LeveeProposee,
    avancer,
    cle_hypothese,
    est_doublon_hypothese,
    est_terminale,
    extraire_hypotheses,
    extraire_levees_proposees,
    verifier_lot_interview,
)

# --- machine à états pure ---


def test_oui_avance_dans_l_ordre_du_prompt() -> None:
    etape = ETAPES[0]
    parcours = [etape]
    for _ in range(len(ETAPES) - 1):
        etape = avancer(etape, valide=True)
        parcours.append(etape)
    assert parcours == list(ETAPES)


def test_non_itere_sur_place() -> None:
    assert avancer("redaction", valide=False) == "redaction"


def test_la_synthese_est_terminale() -> None:
    assert avancer("synthese", valide=True) == "synthese"
    assert est_terminale("synthese")
    assert not est_terminale("interview")


def test_etape_inconnue_refusee() -> None:
    with pytest.raises(ValueError, match="étape inconnue"):
        avancer("etape_fantome", valide=True)


def test_extraction_des_hypotheses() -> None:
    texte = (
        "Statuts : Déposée, Validée [HYPOTHÈSE À VALIDER]\n"
        "Ligne sans marqueur.\n"
        "Taille max : 10 Mo [HYPOTHÈSE À VALIDER]"
    )
    assert len(extraire_hypotheses(texte)) == 2


def test_les_entetes_markdown_ne_sont_pas_des_hypotheses() -> None:
    # Session 11 (06/07/2026) : un titre de section citant le marqueur
    # (« ### 🔎 Hypothèses encore en attente… ») entrait au registre.
    texte = (
        "### 🔎 Hypothèses encore en attente de validation ([HYPOTHÈSE À VALIDER])\n"
        "- Le seuil est de 10 Mo [HYPOTHÈSE À VALIDER]"
    )
    assert extraire_hypotheses(texte) == ["- Le seuil est de 10 Mo [HYPOTHÈSE À VALIDER]"]


def test_les_consignes_ne_sont_pas_des_hypotheses() -> None:
    # Bruit du registre constaté en session de validation (06/07/2026) : le
    # marqueur cité comme convention n'est pas une hypothèse à lever.
    texte = (
        "- Le seuil est de 10 Mo [HYPOTHÈSE À VALIDER]\n"
        "*(Si une donnée vous échappe, je la marquerai [HYPOTHÈSE À VALIDER].)*\n"
        "les lignes vides seront considérées comme [HYPOTHÈSE À VALIDER]\n"
        "Les stories portent la mention [HYPOTHÈSE À VALIDER] car à confirmer."
    )
    assert extraire_hypotheses(texte) == ["- Le seuil est de 10 Mo [HYPOTHÈSE À VALIDER]"]


def test_cle_hypothese_neutralise_la_decoration_markdown() -> None:
    # La même hypothèse en puce, en ligne de tableau ou en récapitulatif gras
    # ne doit produire qu'UNE entrée au registre (déduplication par clé).
    puce = "- Le seuil d'inactivité est de 30 minutes **[HYPOTHÈSE À VALIDER]**."
    tableau = "| Le seuil d'inactivité est de 30 minutes [HYPOTHÈSE À VALIDER] |"
    assert cle_hypothese(puce) == cle_hypothese(tableau)
    assert cle_hypothese(puce) != cle_hypothese("- Autre seuil [HYPOTHÈSE À VALIDER]")


def test_lot_interview_limite_a_3_questions() -> None:
    assert verifier_lot_interview("Q1 ? Q2 ? Q3 ?") == []
    violations = verifier_lot_interview("Q1 ? Q2 ? Q3 ? Q4 ?")
    assert violations and "règle 1" in violations[0]


# --- dédup sémantique du registre (S2.15, paires réelles session 11) ---


def test_reformulation_de_recapitulatif_est_un_doublon() -> None:
    # Paires observées session 11 (06/07/2026) : les récapitulatifs re-listent
    # les hypothèses déjà enregistrées sous d'autres mots (18 « en attente »).
    existants = ["- Taille maximale d'une pièce jointe : 10 Mo [HYPOTHÈSE À VALIDER]"]
    recapitulatif = (
        "- **#3** : Taille maximale de la pièce jointe = 10 Mo, comme indiqué "
        "dans les critères d'acceptation de la Feature [HYPOTHÈSE À VALIDER]."
    )
    assert est_doublon_hypothese(recapitulatif, existants)


def test_ligne_de_tableau_reformulee_est_un_doublon() -> None:
    existants = [
        "Proposition : [HYPOTHÈSE À VALIDER] Création d'un jeu de 20 dossiers "
        "(10 avec email valide, 10 sans email)."
    ]
    recapitulatif = (
        "- **#1** : *Jeu de données* – 20 dossiers (10 avec email valide, 10 sans) "
        "[HYPOTHÈSE À VALIDER]."
    )
    assert est_doublon_hypothese(recapitulatif, existants)


def test_hypothese_distincte_jamais_avalee() -> None:
    # La dédup ne doit JAMAIS absorber une hypothèse réellement nouvelle :
    # ce serait une perte, contraire à A8.
    existants = ["- Taille maximale d'une pièce jointe : 10 Mo [HYPOTHÈSE À VALIDER]"]
    nouvelle = "- Notification par courriel à chaque changement de statut [HYPOTHÈSE À VALIDER]"
    assert not est_doublon_hypothese(nouvelle, existants)
    assert not est_doublon_hypothese("texte sans termes", [])


# --- levées proposées (rapprochement décision d'interview ↔ registre, A8) ---


def test_levee_proposee_extraite_et_filtree_sur_le_registre() -> None:
    texte = (
        "Votre réponse fixe le seuil à 10 Mo.\n"
        "[LEVÉE PROPOSÉE : #3 — confirmée — le PO a fixé le seuil à 10 Mo]\n"
        "[LEVÉE PROPOSÉE : #99 — rejetée — identifiant hors registre]"
    )
    # #99 n'est pas en attente (le modèle peut se tromper de numéro) : ignoré.
    assert extraire_levees_proposees(texte, {3, 4}) == [
        LeveeProposee(3, "confirmee", "le PO a fixé le seuil à 10 Mo")
    ]


def test_levee_proposee_rejet_et_justification_optionnelle() -> None:
    assert extraire_levees_proposees("[LEVÉE PROPOSÉE : #4 — rejetée]", {4}) == [
        LeveeProposee(4, "rejetee", "")
    ]


def test_levee_proposee_malformee_ou_dupliquee_ignoree() -> None:
    texte = (
        "[LEVÉE PROPOSÉE : sans numéro — confirmée]\n"
        "[LEVÉE PROPOSÉE : #5 — peut-être — statut inconnu]\n"
        "[LEVÉE PROPOSÉE : #5 — confirmée — première proposition]\n"
        "[LEVÉE PROPOSÉE : #5 — rejetée — doublon, la première gagne]"
    )
    assert extraire_levees_proposees(texte, {5}) == [
        LeveeProposee(5, "confirmee", "première proposition")
    ]


# --- API (DB scriptée, pattern des tests projets) ---


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


def test_liste_des_sessions_pour_l_accueil(brancher) -> None:
    # Sans liste, une session perdue de vue ne se retrouve que par URL devinée
    # (constaté session de validation, 06/07/2026).
    brancher([[(7, "interview", None, "F" * 130), (5, "synthese", 1, "Feature courte")]])
    reponse = client.get("/workflows")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert [session["id"] for session in corps] == [7, 5]
    assert corps[0]["apercu_feature"] == "F" * 120 + "…"  # aperçu tronqué
    assert corps[1]["apercu_feature"] == "Feature courte"


def test_creation_session_enregistre_les_hypotheses_de_la_feature(brancher) -> None:
    connexion = brancher(
        [
            (7,),  # INSERT session RETURNING id
            (7, "recuperation_feature", None),  # _lire_session : session
            [(1, "Formats : PDF [HYPOTHÈSE À VALIDER]", "po", "en_attente", None, None)],
        ]
    )
    reponse = client.post(
        "/workflows",
        json={"feature": "Ma Feature\nFormats : PDF [HYPOTHÈSE À VALIDER]"},
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["etape"] == "recuperation_feature"
    assert corps["nb_en_attente"] == 1
    requetes = [r for r, _ in connexion.curseur.requetes]
    assert any("INSERT INTO workflow_hypotheses" in r for r in requetes)
    assert connexion.commits == 1


def test_validation_oui_avance_sans_lever_les_hypotheses(brancher) -> None:
    hypothese = (3, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]", "modele", "en_attente", None, None)
    connexion = brancher(
        [
            (7, "interview", None),  # _lire_session avant
            [hypothese],
            (7, "stories_candidates", None),  # _lire_session après
            [hypothese],  # TOUJOURS en_attente : la validation globale ne lève rien (A8)
        ]
    )
    reponse = client.post("/workflows/7/avancer", json={"valide": True})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["etape"] == "stories_candidates"
    assert corps["hypotheses"][0]["statut"] == "en_attente"  # invariant A8
    maj = [p for r, p in connexion.curseur.requetes if "UPDATE workflow_sessions" in r]
    assert maj[0]["etape"] == "stories_candidates"


def test_validation_non_reste_sur_l_etape(brancher) -> None:
    connexion = brancher([(7, "redaction", None), [], (7, "redaction", None), []])
    reponse = client.post(
        "/workflows/7/avancer", json={"valide": False, "commentaire": "revoir le CA2"}
    )
    assert reponse.status_code == 200
    assert reponse.json()["etape"] == "redaction"
    assert any(
        "INSERT INTO workflow_messages" in r for r, _ in connexion.curseur.requetes
    )  # le commentaire du PO est conservé (itération règle 5)


def test_validation_journalisee_pour_la_telemetrie(brancher) -> None:
    # S2.10 : chaque Oui/Non entre dans workflow_validations — la part des
    # « Non » est le proxy v0 du taux d'édition (E4.4).
    connexion = brancher([(7, "redaction", None), [], (7, "redaction", None), []])
    client.post("/workflows/7/avancer", json={"valide": False, "commentaire": "revoir"})
    journal = [p for r, p in connexion.curseur.requetes if "INSERT INTO workflow_validations" in r]
    assert journal == [{"id": 7, "etape": "redaction", "valide": False, "commentaire": "revoir"}]


def test_decision_individuelle_leve_une_hypothese(brancher) -> None:
    connexion = brancher(
        [
            (3,),  # UPDATE ... RETURNING id
            (7, "interview", None),
            [(3, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]", "modele", "confirmee", None, None)],
        ]
    )
    reponse = client.post("/workflows/7/hypotheses/3", json={"statut": "confirmee"})
    assert reponse.status_code == 200
    assert reponse.json()["hypotheses"][0]["statut"] == "confirmee"
    maj = [p for r, p in connexion.curseur.requetes if "UPDATE workflow_hypotheses" in r]
    assert maj[0] == {"hid": 3, "sid": 7, "statut": "confirmee"}


def test_levee_proposee_exposee_sans_lever_l_hypothese(brancher) -> None:
    # La proposition du moteur (S2.13) est visible dans l'état de session pour
    # que l'écran l'affiche à côté des boutons — le statut reste en_attente (A8).
    brancher(
        [
            (7, "interview", None),
            [
                (
                    3,
                    "Seuil 10 Mo [HYPOTHÈSE À VALIDER]",
                    "modele",
                    "en_attente",
                    "confirmee",
                    "le PO a fixé 10 Mo",
                )
            ],
        ]
    )
    corps = client.get("/workflows/7").json()
    hypothese = corps["hypotheses"][0]
    assert hypothese["statut"] == "en_attente"  # invariant A8 : proposée ≠ levée
    assert hypothese["statut_propose"] == "confirmee"
    assert hypothese["justification_proposee"] == "le PO a fixé 10 Mo"
    assert corps["nb_en_attente"] == 1


def test_decision_hypothese_inconnue_404(brancher) -> None:
    brancher([None])
    assert client.post("/workflows/7/hypotheses/99", json={"statut": "rejetee"}).status_code == 404


def test_synthese_refusee_avant_l_etape_finale(brancher) -> None:
    brancher([(7, "redaction", None), []])
    reponse = client.get("/workflows/7/synthese")
    assert reponse.status_code == 409


def test_synthese_recapitule_les_hypotheses_non_levees(brancher) -> None:
    brancher(
        [
            (7, "synthese", None),
            [
                (1, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]", "modele", "en_attente", None, None),
                (2, "Statuts [HYPOTHÈSE À VALIDER]", "po", "confirmee", None, None),
            ],
        ]
    )
    reponse = client.get("/workflows/7/synthese")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps["hypotheses_non_levees"]) == 1  # seule l'en_attente est récapitulée
    assert "arbitrage A8" in corps["avertissement"]


def test_session_inconnue_404(brancher) -> None:
    brancher([None])
    assert client.get("/workflows/99").status_code == 404


def test_lecture_du_fil(brancher) -> None:
    brancher(
        [
            (7, "interview", None),  # _lire_session (contrôle d'existence)
            [],
            [
                (1, "po", "recuperation_feature", "Ma feature"),
                (2, "assistant", "interview", "Q1 ?"),
            ],
            [],  # aucune trace persistée (S3.9)
        ]
    )
    reponse = client.get("/workflows/7/messages")
    assert reponse.status_code == 200
    fil = reponse.json()
    assert [message["role"] for message in fil] == ["po", "assistant"]
    assert fil[1]["contenu"] == "Q1 ?"


def test_lecture_du_fil_avec_traces_persistees(brancher) -> None:
    # S3.9 (A3 complet) : sources — avec l'extrait exact — avertissements et
    # divergences reviennent avec le fil au rechargement (fin de la v1 S2.8).
    brancher(
        [
            (7, "interview", None),
            [],
            [(2, "assistant", "interview", "Réponse sourcée")],
            [
                (2, "source", "spec_v2.docx", "Spec > CA", "le délai est de 30 jours", None),
                (2, "avertissement", None, None, None, "Budget dépassé"),
                (2, "divergence", None, None, None, "[DIVERGENCE] 15 vs 30 jours [Source : spec]"),
            ],
        ]
    )
    fil = client.get("/workflows/7/messages").json()
    message = fil[0]
    assert message["sources"] == [
        {"nom": "spec_v2.docx", "section": "Spec > CA", "extrait": "le délai est de 30 jours"}
    ]
    assert message["avertissements"] == ["Budget dépassé"]
    assert len(message["divergences"]) == 1
