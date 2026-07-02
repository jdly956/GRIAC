"""Tests S1.9 : qualification v0 — métadonnées, doublons par hash, versions, référence."""

from datetime import date

import pytest

from sia_ingestion.qualify import (
    LigneDocument,
    enregistrer_qualifications,
    extraire_date_nom,
    lire_inventaire,
    main,
    normaliser_groupe,
    qualifier_document,
    qualifier_lot,
)


def _ligne(chemin: str, sha256: str = "x" * 64, mtime: str = "2026-07-01T10:00:00+00:00"):
    return LigneDocument(chemin=chemin, nom=chemin.rsplit("/", 1)[-1], mtime=mtime, sha256=sha256)


# --- Jeu de fixtures piégé (CA4) : spec_v1, spec_v2_final_VF3, copie conforme ---

JEU_PIEGE = [
    _ligne("projet-alpha/spec-authentification_v1.docx", sha256="a" * 64),
    _ligne("projet-alpha/spec-authentification_v2_final_VF3.docx", sha256="b" * 64),
    _ligne("projet-alpha/spec-authentification_v2_final_VF3 - Copie.docx", sha256="b" * 64),
    _ligne("projet-beta/notes-reunion-2026-06-15.txt", sha256="c" * 64),
]


def test_jeu_piege_correctement_qualifie() -> None:
    resultats = {q.chemin: q for q in qualifier_lot(JEU_PIEGE)}

    v1 = resultats["projet-alpha/spec-authentification_v1.docx"]
    v2 = resultats["projet-alpha/spec-authentification_v2_final_VF3.docx"]
    copie = resultats["projet-alpha/spec-authentification_v2_final_VF3 - Copie.docx"]
    notes = resultats["projet-beta/notes-reunion-2026-06-15.txt"]

    # Même groupe de versions pour les trois specs (similarité de nom)
    assert v1.groupe_version == v2.groupe_version == copie.groupe_version

    # Copie conforme : doublon par hash, jamais référence
    assert copie.doublon_de == v2.chemin
    assert copie.est_reference is False
    assert v2.doublon_de is None

    # La plus récente (v2, finale, VF3) est la référence ; la v1 non
    assert v2.est_reference is True
    assert v1.est_reference is False
    assert (v2.version_no, v2.marque_finale) == (2, True)
    assert (v1.version_no, v1.marque_finale) == (1, False)

    # Projet suggéré = 1er niveau du chemin — une suggestion (A6), pas une affectation
    assert v2.projet_suggere == "projet-alpha"
    assert notes.projet_suggere == "projet-beta"

    # Date portée par le nom
    assert notes.date_nom == date(2026, 6, 15)


def test_statut_brouillon_detecte() -> None:
    for nom in ("spec_draft.docx", "note-BROUILLON.docx", "WIP-cadrage.docx"):
        assert qualifier_document(_ligne(f"p/{nom}")).statut_brouillon is True
    assert qualifier_document(_ligne("p/spec_v2.docx")).statut_brouillon is False


def test_brouillon_jamais_reference_face_a_une_version_propre() -> None:
    lignes = [
        _ligne("p/spec_v3_draft.docx", sha256="d" * 64),
        _ligne("p/spec_v2.docx", sha256="e" * 64),
    ]
    resultats = {q.chemin: q for q in qualifier_lot(lignes)}
    assert resultats["p/spec_v2.docx"].est_reference is True
    assert resultats["p/spec_v3_draft.docx"].est_reference is False


def test_extraction_dates() -> None:
    assert extraire_date_nom("rapport-2026-06-15.pdf") == date(2026, 6, 15)
    assert extraire_date_nom("rapport_20260615.pdf") == date(2026, 6, 15)
    assert extraire_date_nom("rapport 15-06-2026.pdf") == date(2026, 6, 15)
    assert extraire_date_nom("rapport-sans-date.pdf") is None


def test_normalisation_groupe_version() -> None:
    assert (
        normaliser_groupe("Spec-Authentification_v2_final_VF3 - Copie.docx")
        == normaliser_groupe("spec-authentification_v1.docx")
        == "spec-authentification"
    )
    # Deux documents différents ne se regroupent pas
    assert normaliser_groupe("guide-installation.pdf") != normaliser_groupe(
        "spec-authentification_v1.docx"
    )


def test_document_racine_sans_projet() -> None:
    assert qualifier_document(_ligne("note-racine.txt")).projet_suggere is None


def test_groupes_distincts_par_projet() -> None:
    # Même nom dans deux projets : deux groupes, deux références
    lignes = [
        _ligne("projet-alpha/spec_v1.docx", sha256="f" * 64),
        _ligne("projet-beta/spec_v1.docx", sha256="g" * 64),
    ]
    resultats = qualifier_lot(lignes)
    assert all(q.est_reference for q in resultats)


class FauxCurseur:
    def __init__(self, lignes) -> None:
        self.lignes = lignes
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres or {}))

    def fetchall(self):
        return self.lignes

    def __enter__(self) -> "FauxCurseur":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, lignes=None) -> None:
        self.curseur = FauxCurseur(lignes or [])
        self.commits = 0

    def cursor(self) -> FauxCurseur:
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


def test_lecture_et_ecriture_en_base() -> None:
    connexion = FausseConnexion([("p/a.docx", "a.docx", "2026-07-01T10:00:00+00:00", "a" * 64)])
    lignes = lire_inventaire(connexion)
    assert lignes[0].nom == "a.docx"

    enregistrer_qualifications(connexion, qualifier_lot(lignes))
    requete, parametres = connexion.curseur.requetes[-1]
    assert "SET projet_suggere" in requete
    assert parametres["chemin"] == "p/a.docx"
    assert parametres["est_reference"] is True
    assert connexion.commits == 1


def test_main_exige_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL absente" in capsys.readouterr().err
