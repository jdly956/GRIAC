"""Tests S2.9 : inventaire documents pour l'écran E4.3 — DB simulée."""

from collections import deque

import pytest
from fastapi.testclient import TestClient

from sia_api.db import get_connexion
from sia_api.main import app

client = TestClient(app)


class FauxCurseur:
    """File de résultats rejoués dans l'ordre des fetchone/fetchall du code."""

    def __init__(self, resultats: deque) -> None:
        self.resultats = resultats
        self.requetes: list[str] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append(requete)

    def fetchone(self):
        return self.resultats.popleft()

    def fetchall(self):
        return self.resultats.popleft()

    def __enter__(self) -> "FauxCurseur":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, resultats: list) -> None:
        self.curseur = FauxCurseur(deque(resultats))
        self.commits = 0

    def cursor(self) -> FauxCurseur:
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> FausseConnexion:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        return connexion

    yield _brancher
    app.dependency_overrides.clear()


def test_liste_documents_expose_statuts_reference_doublon(brancher) -> None:
    # Tuples étendus mécaniquement avec est_obsolete (R8) — assertions intactes.
    brancher(
        [
            [
                (1, "pa/spec-v2.docx", "spec-v2.docx", "docx", "parse", True, False, "pa", False),
                (2, "pa/spec-v1.docx", "spec-v1.docx", "docx", "parse", False, True, "pa", False),
                (3, "divers/scan.pdf", "scan.pdf", "pdf", "ocr_requis", False, False, None, True),
            ]
        ]
    )
    reponse = client.get("/documents")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 3
    assert corps[0] == {
        "id": 1,  # S3.14 : l'inventaire pointe vers la fiche /documents/{id}
        "chemin": "pa/spec-v2.docx",
        "nom": "spec-v2.docx",
        "extension": "docx",
        "statut_parsing": "parse",
        "est_reference": True,
        "doublon": False,
        "projet_suggere": "pa",
        "est_obsolete": False,
    }
    assert corps[1]["doublon"] is True
    assert corps[2]["statut_parsing"] == "ocr_requis"
    assert corps[2]["projet_suggere"] is None
    assert corps[2]["est_obsolete"] is True  # R8 : exposé pour le badge/bascule


def test_marquer_obsolete_et_reactiver(brancher) -> None:
    # R8 (H10) : PATCH bascule est_obsolete — réversible, 404 si inconnu.
    connexion = brancher([(1,)])
    reponse = client.patch("/documents/1", json={"est_obsolete": True})
    assert reponse.status_code == 200
    assert reponse.json() == {"id": 1, "est_obsolete": True}
    assert any("SET est_obsolete" in requete for requete in connexion.curseur.requetes)
    assert connexion.commits == 1

    brancher([(1,)])
    assert client.patch("/documents/1", json={"est_obsolete": False}).status_code == 200
    brancher([None])
    assert client.patch("/documents/99", json={"est_obsolete": True}).status_code == 404


def test_fiche_document_traitement_complet(brancher, tmp_path) -> None:
    # S3.14 : la fiche restitue le parsing (dérivé markdown lu du disque) et
    # les chunks avec leur état d'embedding.
    derive = tmp_path / "abc.md"
    derive.write_text("# Titre parsé\n\ncontenu du dérivé", encoding="utf-8")
    brancher(
        [
            (
                1,
                "pa/spec-v2.docx",
                "spec-v2.docx",
                "docx",
                12_345,
                "abc123",
                "parse",
                None,
                "2026-07-06 22:00",
                str(derive),
                True,
                None,
                "pa",
                2,
                "spec",
                False,  # est_obsolete (R8) — extension mécanique du tuple
            ),
            [
                (0, "Spec > Exigences", 640, "contenu du chunk 0", True),
                (1, "Spec > CA", 512, "contenu du chunk 1", False),
            ],
        ]
    )
    corps = client.get("/documents/1").json()
    assert corps["derive_apercu"].startswith("# Titre parsé")
    assert corps["derive_tronque"] is False
    assert corps["nb_chunks"] == 2 and corps["nb_embarques"] == 1
    assert corps["chunks"][0]["section"] == "Spec > Exigences"
    assert corps["chunks"][1]["embarque"] is False
    assert corps["version_no"] == 2 and corps["est_reference"] is True


def test_fiche_document_derive_absent_reste_consultable(brancher) -> None:
    # Pod recréé : le fichier dérivé a disparu — la fiche le dit sans échouer.
    brancher(
        [
            (
                1,
                "divers/scan.pdf",
                "scan.pdf",
                "pdf",
                999,
                "def456",
                "ocr_requis",
                "PDF scanné : OCR Albert requis",
                None,
                "/parti/avec/le/pod.md",
                False,
                None,
                None,
                None,
                None,
                False,  # est_obsolete (R8) — extension mécanique du tuple
            ),
            [],
        ]
    )
    corps = client.get("/documents/1").json()
    assert corps["derive_apercu"] is None
    assert corps["erreur_parsing"] == "PDF scanné : OCR Albert requis"
    assert corps["nb_chunks"] == 0


def test_fiche_document_inconnue_404(brancher) -> None:
    brancher([None])
    assert client.get("/documents/99").status_code == 404


def test_liste_dossiers_union_disque_et_base(brancher, tmp_path, monkeypatch) -> None:
    # S3.18 : la datalist du dépôt fusionne les dossiers du disque (créés,
    # même pas encore indexés) et ceux vus par la qualification (base).
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path))
    (tmp_path / "projet-alpha").mkdir()
    (tmp_path / "tout-nouveau").mkdir()
    (tmp_path / "un-fichier.txt").write_text("pas un dossier", encoding="utf-8")
    brancher([[("projet-alpha",), ("projet-beta",)]])
    reponse = client.get("/documents/dossiers")
    assert reponse.status_code == 200  # la route dynamique {id} ne capture pas « dossiers »
    assert reponse.json() == ["projet-alpha", "projet-beta", "tout-nouveau"]


def test_telechargement_original(brancher, tmp_path, monkeypatch) -> None:
    # S3.17 : l'original est servi tel que déposé, sous son nom.
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path))
    (tmp_path / "pa").mkdir()
    (tmp_path / "pa" / "spec-v2.docx").write_bytes(b"contenu original")
    brancher([("pa/spec-v2.docx", "spec-v2.docx")])
    reponse = client.get("/documents/1/original")
    assert reponse.status_code == 200
    assert reponse.content == b"contenu original"
    assert "spec-v2.docx" in reponse.headers["content-disposition"]


def test_telechargement_original_fichier_absent_404(brancher, tmp_path, monkeypatch) -> None:
    # Pod recréé : la ligne existe mais le fichier source a disparu — 404 explicite.
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path))
    brancher([("pa/parti.docx", "parti.docx")])
    reponse = client.get("/documents/1/original")
    assert reponse.status_code == 404
    assert "absent du corpus" in reponse.json()["detail"]


def test_telechargement_original_chemin_hors_corpus_404(brancher, tmp_path, monkeypatch) -> None:
    # Garde-fou : un chemin qui sort de la racine corpus n'est jamais servi.
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path / "corpus"))
    (tmp_path / "corpus").mkdir()
    (tmp_path / "secret.txt").write_text("hors corpus", encoding="utf-8")
    brancher([("../secret.txt", "secret.txt")])
    assert client.get("/documents/1/original").status_code == 404


def test_suppression_document_base_et_fichiers(brancher, tmp_path, monkeypatch) -> None:
    # S3.17 : suppression = ligne (chunks en cascade), doublons repointés,
    # fichier source ET dérivé retirés du disque (sinon ré-inventoriés, D9).
    monkeypatch.setenv("SIA_CORPUS_DIR", str(tmp_path / "corpus"))
    source = tmp_path / "corpus" / "pa" / "spec-v2.docx"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original")
    derive = tmp_path / "derives" / "abc.md"
    derive.parent.mkdir()
    derive.write_text("# dérivé", encoding="utf-8")
    connexion = brancher([("pa/spec-v2.docx", str(derive))])
    reponse = client.delete("/documents/1")
    assert reponse.status_code == 204
    assert not source.exists() and not derive.exists()
    requetes = " ; ".join(connexion.curseur.requetes)
    assert "SET doublon_de = NULL" in requetes
    assert "DELETE FROM documents" in requetes
    assert connexion.commits == 1


def test_suppression_document_inconnu_404(brancher) -> None:
    brancher([None])
    assert client.delete("/documents/99").status_code == 404


def test_stats_documents_calcule_la_couverture(brancher) -> None:
    # 10 documents dont 8 parsables : 6 parsés, 1 échec, 1 OCR requis ; 4 références.
    brancher([(10, 8, 6, 1, 1, 4)])
    reponse = client.get("/documents/stats")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] == 10
    assert corps["parsables"] == 8
    assert corps["parses"] == 6
    assert corps["echecs"] == 1
    assert corps["ocr_requis"] == 1
    assert corps["references"] == 4
    assert corps["couverture_parsing"] == 0.75


def test_stats_corpus_vide_couverture_pleine(brancher) -> None:
    # Aucun document parsable : pas de division par zéro, couverture affichée à 1.0.
    brancher([(2, 0, 0, 0, 0, 0)])
    reponse = client.get("/documents/stats")
    assert reponse.status_code == 200
    assert reponse.json()["couverture_parsing"] == 1.0
