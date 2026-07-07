"""Tests S1.11 : CRUD projets/NFR/dossiers — DB simulée via dependency_overrides."""

from collections import deque

import psycopg
import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app

client = TestClient(app)


class FauxCurseur:
    """File de résultats rejoués dans l'ordre des fetchone/fetchall du code."""

    def __init__(self, resultats: deque, echoue_sur: str | None = None) -> None:
        self.resultats = resultats
        self.echoue_sur = echoue_sur
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        if self.echoue_sur and self.echoue_sur in requete:
            raise psycopg.errors.UniqueViolation("nom déjà pris")
        self.requetes.append((requete, parametres or {}))

    def fetchone(self):
        return self.resultats.popleft()

    def fetchall(self):
        return self.resultats.popleft()

    def __enter__(self) -> "FauxCurseur":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, resultats: list, echoue_sur: str | None = None) -> None:
        self.curseur = FauxCurseur(deque(resultats), echoue_sur)
        self.commits = 0

    def cursor(self) -> FauxCurseur:
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


@pytest.fixture
def brancher():
    """Branche une fausse connexion sur l'app ; nettoie l'override après le test."""

    def _brancher(resultats: list, echoue_sur: str | None = None) -> FausseConnexion:
        connexion = FausseConnexion(resultats, echoue_sur)
        app.dependency_overrides[get_connexion] = lambda: connexion
        return connexion

    yield _brancher
    app.dependency_overrides.clear()


PROJET_ENTREE = {
    "nom": "SIA PO",
    "contexte": "Assistant de rédaction de user stories.",
    "nfrs": [{"type": "performance", "formulation": "p95 < 1 s", "valeur_cible": "1 s"}],
    "dossiers": [{"dossier": "projet-alpha", "origine": "suggestion"}],
}

# Tuple projet étendu mécaniquement avec `archive` (R9) — assertions intactes.
LECTURE_PROJET = [
    (1, "SIA PO", "Assistant de rédaction de user stories.", False),
    [("performance", "p95 < 1 s", "1 s")],
    [("projet-alpha", "suggestion")],
]


def test_creation_projet_complet(brancher) -> None:
    connexion = brancher([(1,), *LECTURE_PROJET])
    reponse = client.post("/projects", json=PROJET_ENTREE)
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["id"] == 1
    assert corps["nfrs"][0]["type"] == "performance"
    assert corps["dossiers"][0] == {"dossier": "projet-alpha", "origine": "suggestion"}
    assert connexion.commits == 1
    requetes = [requete for requete, _ in connexion.curseur.requetes]
    assert any("INSERT INTO projects" in requete for requete in requetes)
    assert any("INSERT INTO project_nfrs" in requete for requete in requetes)
    assert any("INSERT INTO project_dossiers" in requete for requete in requetes)


def test_creation_nom_duplique_409(brancher) -> None:
    brancher([], echoue_sur="INSERT INTO projects")
    reponse = client.post("/projects", json=PROJET_ENTREE)
    assert reponse.status_code == 409


def test_creation_nom_vide_422(brancher) -> None:
    brancher([])
    assert client.post("/projects", json={"nom": ""}).status_code == 422


def test_type_nfr_invalide_422(brancher) -> None:
    brancher([])
    entree = {"nom": "X", "nfrs": [{"type": "esthetique", "formulation": "joli"}]}
    assert client.post("/projects", json=entree).status_code == 422


def test_lecture_projet_absent_404(brancher) -> None:
    brancher([None])
    assert client.get("/projects/99").status_code == 404


def test_lecture_projet_complet(brancher) -> None:
    brancher(list(LECTURE_PROJET))
    reponse = client.get("/projects/1")
    assert reponse.status_code == 200
    assert reponse.json()["nom"] == "SIA PO"


def test_maj_remplace_nfrs_et_dossiers(brancher) -> None:
    connexion = brancher([(1,), *LECTURE_PROJET])
    reponse = client.put("/projects/1", json=PROJET_ENTREE)
    assert reponse.status_code == 200
    requetes = [requete for requete, _ in connexion.curseur.requetes]
    assert any("UPDATE projects SET" in requete for requete in requetes)
    assert any("DELETE FROM project_nfrs" in requete for requete in requetes)
    assert any("DELETE FROM project_dossiers" in requete for requete in requetes)
    assert connexion.commits == 1


def test_maj_projet_absent_404(brancher) -> None:
    connexion = brancher([None])
    assert client.put("/projects/99", json=PROJET_ENTREE).status_code == 404
    assert connexion.commits == 0


def test_archiver_et_desarchiver_un_projet(brancher) -> None:
    # R9 (UX8) : PATCH archive — masqué des listes (et du choix à la création
    # de session), réversible, jamais détruit ; 404 si inconnu.
    connexion = brancher([(1,)])
    reponse = client.patch("/projects/1", json={"archive": True})
    assert reponse.status_code == 200
    assert reponse.json() == {"id": 1, "archive": True}
    requete, parametres = connexion.curseur.requetes[0]
    assert "SET archive" in requete and parametres == {"id": 1, "archive": True}
    brancher([None])
    assert client.patch("/projects/99", json={"archive": True}).status_code == 404


def test_liste_des_projets_archives(brancher) -> None:
    # R9 : ?archives=true — le défaut reste les projets actifs.
    connexion = brancher([[(1,)], *LECTURE_PROJET])
    reponse = client.get("/projects", params={"archives": "true"})
    assert reponse.status_code == 200
    requete, parametres = connexion.curseur.requetes[0]
    assert "WHERE archive = %(archives)s" in requete and parametres == {"archives": True}


def test_suppression_definitive_de_projet(brancher) -> None:
    # R9 (H9, « suppression libre ») : DELETE — NFR/dossiers en cascade (0005),
    # les sessions liées passent à projet_id NULL (0008) et continuent sans
    # contexte projet ; 404 si inconnu.
    connexion = brancher([(1,)])
    assert client.delete("/projects/1").status_code == 204
    requete, parametres = connexion.curseur.requetes[0]
    assert "DELETE FROM projects" in requete and parametres == {"id": 1}
    assert connexion.commits == 1
    brancher([None])
    assert client.delete("/projects/99").status_code == 404


def test_suggestions_dossiers_a6(brancher) -> None:
    brancher([[("projet-alpha", 3, False), ("projet-beta", 3, True)]])
    reponse = client.get("/dossiers/suggestions")
    assert reponse.status_code == 200
    assert reponse.json() == [
        {"dossier": "projet-alpha", "nb_documents": 3, "deja_associe": False},
        {"dossier": "projet-beta", "nb_documents": 3, "deja_associe": True},
    ]


def test_sans_database_url_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reponse = client.get("/projects")
    assert reponse.status_code == 503
    assert "DATABASE_URL absente" in reponse.json()["detail"]
