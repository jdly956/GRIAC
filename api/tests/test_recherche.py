"""Tests S2.3 : fusion RRF, recherche hybride (DB et Albert simulés), filtres A6."""

from collections import deque
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app
from sia_api.recherche import RechercheEntree, fusion_rrf, get_albert, rechercher

# --- fusion RRF (fonction pure) ---


def test_fusion_rrf_recompense_le_consensus() -> None:
    fusion = fusion_rrf([[1, 2, 3], [2, 1, 4]], k=60)
    identifiants = [identifiant for identifiant, _ in fusion]
    assert set(identifiants[:2]) == {1, 2}  # présents en tête des deux volets
    assert identifiants[2:] == [3, 4]


def test_fusion_rrf_ordre_deterministe_a_score_egal() -> None:
    assert [i for i, _ in fusion_rrf([[5], [7]])] == [5, 7]


def test_fusion_rrf_vide() -> None:
    assert fusion_rrf([[], []]) == []


# --- doubles de test DB / Albert ---


class FauxCurseur:
    def __init__(self, resultats: deque) -> None:
        self.resultats = resultats
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres or {}))

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


class FauxAlbert:
    def __init__(self) -> None:
        self.appels: list[dict] = []
        self.embeddings = SimpleNamespace(create=self._creer)

    def _creer(self, **kwargs):
        self.appels.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.5] * 4)])


def _settings():
    from sia_api.config import Settings

    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        albert_base_url="https://albert.example/v1",
        albert_api_key="cle-de-test",
    )


DETAILS = [
    (1, "projet-alpha/spec_v2.docx", "spec_v2.docx", "Spec > CA", "contenu un", 120),
    (2, "projet-alpha/spec_v1.docx", "spec_v1.docx", "Spec", "contenu deux", 80),
]


def test_recherche_hybride_fusionne_et_trace_les_sources() -> None:
    connexion = FausseConnexion([[(1,), (2,)], [(2,), (1,)], DETAILS])
    client = FauxAlbert()
    resultat = rechercher(
        connexion, client, _settings(), RechercheEntree(question="délai d'instruction")
    )

    assert [chunk.document for chunk in resultat.resultats] == [
        "projet-alpha/spec_v2.docx",
        "projet-alpha/spec_v1.docx",
    ]
    assert resultat.resultats[0].section == "Spec > CA"  # citation document + section
    assert resultat.avertissement is None
    # La question est vectorisée en float (gotcha S1.5), jamais en base64
    assert client.appels[0]["encoding_format"] == "float"
    assert client.appels[0]["input"] == ["délai d'instruction"]
    # Filtre par défaut : statut = référence (tout_statut = False)
    parametres_bm25 = connexion.curseur.requetes[0][1]
    assert parametres_bm25["tout_statut"] is False
    assert parametres_bm25["dossiers"] is None


def test_recherche_filtre_par_projet_a6() -> None:
    connexion = FausseConnexion([[("projet-alpha",)], [(1,)], [(1,)], DETAILS[:1]])
    resultat = rechercher(
        connexion,
        FauxAlbert(),
        _settings(),
        RechercheEntree(question="instruction", projet_id=1),
    )
    requetes = connexion.curseur.requetes
    assert "project_dossiers" in requetes[0][0]  # dossiers confirmés par le PO (S1.11)
    assert requetes[1][1]["dossiers"] == ["projet-alpha"]
    assert len(resultat.resultats) == 1


def test_aucune_source_recuperable_signalee() -> None:
    connexion = FausseConnexion([[], []])
    resultat = rechercher(
        connexion, FauxAlbert(), _settings(), RechercheEntree(question="sujet inconnu")
    )
    assert resultat.resultats == []
    assert "Aucune source récupérable" in (resultat.avertissement or "")


# --- endpoint REST (dependency_overrides) ---

client_http = TestClient(app)


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> None:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        app.dependency_overrides[get_albert] = lambda: (FauxAlbert(), _settings())

    yield _brancher
    app.dependency_overrides.clear()


def test_endpoint_recherche(brancher) -> None:
    brancher([[(1,)], [(1,)], DETAILS[:1]])
    reponse = client_http.post("/recherche", json={"question": "délai d'instruction"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["resultats"][0]["nom"] == "spec_v2.docx"
    assert corps["resultats"][0]["score_rrf"] > 0


def test_endpoint_valide_les_bornes(brancher) -> None:
    brancher([])
    assert client_http.post("/recherche", json={"question": ""}).status_code == 422
    assert (
        client_http.post("/recherche", json={"question": "q", "nb": 50}).status_code == 422
    )  # 8-15 chunks max (budget 20k, E2)
