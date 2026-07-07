"""Tests S3.10 : corpus depuis l'UI — upload, lancement du pipeline, suivi des runs."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

import sia_api.ingestion as ingestion
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


def test_depot_de_document(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path / "corpus"))
    reponse = client.post(
        "/documents/upload",
        files={"fichier": ("spec ../v2.docx", b"contenu docx", "application/msword")},
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["taille"] == len(b"contenu docx")
    # Le nom est neutralisé (aucune traversée de chemin) et le fichier écrit.
    assert (tmp_path / "corpus" / "v2.docx").read_bytes() == b"contenu docx"


def test_depot_extension_refusee(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path))
    reponse = client.post(
        "/documents/upload", files={"fichier": ("script.exe", b"x", "application/x-dosexec")}
    )
    assert reponse.status_code == 422
    assert "refusée" in reponse.json()["detail"]


def test_lancement_du_pipeline(brancher, monkeypatch: pytest.MonkeyPatch) -> None:
    lancements: list[tuple[int, str]] = []
    monkeypatch.setattr(
        ingestion, "_demarrer_pipeline", lambda run_id, corpus: lancements.append((run_id, corpus))
    )
    monkeypatch.setenv("SIA_CORPUS_DIR", "corpus-test")
    connexion = brancher(
        [
            None,  # aucun run en cours
            (4, "en_cours", "corpus-test", {}, "2026-07-06 21:00", None),
        ]
    )
    reponse = client.post("/ingestion/lancer")
    assert reponse.status_code == 202
    assert reponse.json()["id"] == 4
    assert lancements == [(4, "corpus-test")]  # le sous-processus part APRÈS le commit
    assert connexion.commits == 1


def test_un_seul_run_a_la_fois(brancher, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ingestion, "_demarrer_pipeline", lambda *a: pytest.fail("ne doit pas partir")
    )
    brancher([(5,)])  # un run en cours
    reponse = client.post("/ingestion/lancer")
    assert reponse.status_code == 409
    assert "run 5" in reponse.json()["detail"]


def test_liste_des_runs(brancher) -> None:
    brancher(
        [
            [
                (2, "en_cours", "corpus", {"scan": "ok"}, "2026-07-06 21:10", None),
                (
                    1,
                    "termine",
                    "corpus",
                    {"scan": "ok", "embed": "ok"},
                    "2026-07-06 20:00",
                    "2026-07-06 20:12",
                ),
            ]
        ]
    )
    corps = client.get("/ingestion/runs").json()
    assert [run["id"] for run in corps] == [2, 1]
    assert corps[1]["rapport"]["embed"] == "ok"


def test_debloquer_un_run(brancher) -> None:
    brancher([(3, "echec", "corpus", {}, "2026-07-06 21:00", "2026-07-06 21:30")])
    corps = client.post("/ingestion/runs/3/echec").json()
    assert corps["statut"] == "echec"


def test_debloquer_run_inconnu_404(brancher) -> None:
    brancher([None])
    assert client.post("/ingestion/runs/99/echec").status_code == 404
