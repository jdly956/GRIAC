"""Tests E3.1 : machine à états (pur) + API sessions/hypothèses (DB simulée)."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app
from sia_api.workflow import (
    ETAPES,
    avancer,
    est_terminale,
    extraire_hypotheses,
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


def test_lot_interview_limite_a_3_questions() -> None:
    assert verifier_lot_interview("Q1 ? Q2 ? Q3 ?") == []
    violations = verifier_lot_interview("Q1 ? Q2 ? Q3 ? Q4 ?")
    assert violations and "règle 1" in violations[0]


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


def test_creation_session_enregistre_les_hypotheses_de_la_feature(brancher) -> None:
    connexion = brancher(
        [
            (7,),  # INSERT session RETURNING id
            (7, "recuperation_feature", None),  # _lire_session : session
            [(1, "Formats : PDF [HYPOTHÈSE À VALIDER]", "po", "en_attente")],  # hypothèses
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
    hypothese = (3, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]", "modele", "en_attente")
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
            [(3, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]", "modele", "confirmee")],
        ]
    )
    reponse = client.post("/workflows/7/hypotheses/3", json={"statut": "confirmee"})
    assert reponse.status_code == 200
    assert reponse.json()["hypotheses"][0]["statut"] == "confirmee"
    maj = [p for r, p in connexion.curseur.requetes if "UPDATE workflow_hypotheses" in r]
    assert maj[0] == {"hid": 3, "sid": 7, "statut": "confirmee"}


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
                (1, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]", "modele", "en_attente"),
                (2, "Statuts [HYPOTHÈSE À VALIDER]", "po", "confirmee"),
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
            [("po", "recuperation_feature", "Ma feature"), ("assistant", "interview", "Q1 ?")],
        ]
    )
    reponse = client.get("/workflows/7/messages")
    assert reponse.status_code == 200
    fil = reponse.json()
    assert [message["role"] for message in fil] == ["po", "assistant"]
    assert fil[1]["contenu"] == "Q1 ?"
