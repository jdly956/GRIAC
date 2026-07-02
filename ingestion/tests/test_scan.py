"""Tests S1.7 : scan du corpus, upsert (DB simulée), export CSV. Aucune DB réelle."""

import csv
import hashlib
from pathlib import Path

import pytest

from sia_ingestion.scan import (
    FichierInventorie,
    exporter_csv,
    main,
    scanner_dossier,
    upserter_documents,
)

FIXTURES = Path(__file__).parents[2] / "evals" / "fixtures"


def test_scanner_arborescence_locale(tmp_path: Path) -> None:
    (tmp_path / "dossier").mkdir()
    (tmp_path / "dossier" / "Rapport Final.DOCX").write_bytes(b"contenu docx")
    (tmp_path / "racine.txt").write_bytes(b"contenu texte")
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "tmp.txt").write_bytes(b"cache")
    (tmp_path / ".DS_Store").write_bytes(b"pollution")

    inventaire = scanner_dossier(tmp_path)

    assert [f.chemin for f in inventaire] == ["dossier/Rapport Final.DOCX", "racine.txt"]
    fichier = inventaire[0]
    assert fichier.nom == "Rapport Final.DOCX"
    assert fichier.extension == "docx"  # normalisée en minuscules
    assert fichier.taille_octets == len(b"contenu docx")
    assert fichier.sha256 == hashlib.sha256(b"contenu docx").hexdigest()
    assert fichier.mtime.endswith("+00:00")  # UTC


def test_scanner_corpus_introuvable(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError, match="Corpus introuvable"):
        scanner_dossier(tmp_path / "absent")


def test_fixtures_du_repo_doublons_et_versions() -> None:
    inventaire = scanner_dossier(FIXTURES)
    assert len(inventaire) == 6
    par_nom = {f.nom: f for f in inventaire}
    # Doublon : la copie est byte-à-byte identique -> même sha256, chemins distincts
    original = par_nom["spec-authentification_v2_final_VF3.docx"]
    copie = par_nom["spec-authentification_v2_final_VF3 - Copie.docx"]
    assert original.sha256 == copie.sha256
    assert original.chemin != copie.chemin
    # Les versions v1 et v2 sont des contenus différents
    assert par_nom["spec-authentification_v1.docx"].sha256 != original.sha256
    assert {f.extension for f in inventaire} == {"docx", "pdf", "txt"}


class FauxCurseur:
    """Curseur factice : rejoue le RETURNING (xmax = 0) et capture les requêtes."""

    def __init__(self, deja_connus: set[str]) -> None:
        self.deja_connus = deja_connus
        self.requetes: list[tuple[str, dict]] = []
        self._dernier_insere = False

    def execute(self, requete: str, parametres: dict) -> None:
        self.requetes.append((requete, parametres))
        self._dernier_insere = parametres["chemin"] not in self.deja_connus
        self.deja_connus.add(parametres["chemin"])

    def fetchone(self) -> tuple[bool]:
        return (self._dernier_insere,)

    def __enter__(self) -> "FauxCurseur":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, deja_connus: set[str] | None = None) -> None:
        self.curseur = FauxCurseur(deja_connus or set())
        self.commits = 0

    def cursor(self) -> FauxCurseur:
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


def _fichier(chemin: str) -> FichierInventorie:
    return FichierInventorie(
        chemin=chemin,
        nom=chemin.rsplit("/", 1)[-1],
        extension="txt",
        taille_octets=1,
        sha256="0" * 64,
        mtime="2026-07-02T00:00:00+00:00",
    )


def test_upsert_compte_inseres_et_mis_a_jour() -> None:
    connexion = FausseConnexion(deja_connus={"connu.txt"})
    statistiques = upserter_documents(connexion, [_fichier("connu.txt"), _fichier("nouveau.txt")])
    assert statistiques == {"inseres": 1, "mis_a_jour": 1}
    assert connexion.commits == 1
    requete = connexion.curseur.requetes[0][0]
    # L'idempotence repose sur le chemin ; la relance ne crée jamais de doublon.
    assert "ON CONFLICT (chemin) DO UPDATE" in requete
    assert "derniere_vue = now()" in requete


def test_export_csv(tmp_path: Path) -> None:
    chemin_csv = tmp_path / "sous" / "inventaire.csv"
    exporter_csv([_fichier("a.txt"), _fichier("b/c.txt")], chemin_csv)
    lignes = list(csv.DictReader(chemin_csv.open(encoding="utf-8")))
    assert len(lignes) == 2
    assert lignes[1]["chemin"] == "b/c.txt"
    assert lignes[0]["sha256"] == "0" * 64


def test_main_refuse_s3(capsys: pytest.CaptureFixture) -> None:
    assert main(["--corpus", "s3://bucket/corpus"]) == 2
    assert "snapshot MinIO" in capsys.readouterr().err


def test_main_exige_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main(["--corpus", str(tmp_path)]) == 2
    assert "DATABASE_URL absente" in capsys.readouterr().err
