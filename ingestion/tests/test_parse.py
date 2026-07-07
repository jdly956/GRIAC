"""Tests S1.8 : parsing par lot (docling simulé — jamais chargé), statuts, rapport."""

import csv
from pathlib import Path

import pytest

from sia_ingestion.parse import (
    EXTENSIONS_PARSEES,
    ResultatParsing,
    convertir_eml_en_markdown,
    ecrire_rapport,
    enregistrer_resultats,
    est_pdf_sans_texte,
    lire_documents_a_parser,
    main,
    parser_lot,
)

FIXTURES = Path(__file__).parents[2] / "evals" / "fixtures"


def _corpus(tmp_path: Path) -> Path:
    racine = tmp_path / "corpus"
    (racine / "alpha").mkdir(parents=True)
    (racine / "alpha" / "spec.docx").write_bytes(b"docx factice")
    (racine / "alpha" / "guide.pdf").write_bytes(b"pdf factice")
    return racine


def test_lot_nominal_ecrit_les_derives(tmp_path: Path) -> None:
    racine, derives = _corpus(tmp_path), tmp_path / "derives"
    resultats = parser_lot(
        [("alpha/spec.docx", "a" * 64), ("alpha/guide.pdf", "b" * 64)],
        racine,
        derives,
        convertir=lambda _: "# Titre\n\n| a | b |\n|---|---|\n",
        pdf_sans_texte=lambda _: False,
    )
    assert [r.statut for r in resultats] == ["parse", "parse"]
    assert (derives / ("a" * 64 + ".md")).read_text(encoding="utf-8").startswith("# Titre")


def test_echec_isole_n_interrompt_pas_le_lot(tmp_path: Path) -> None:
    racine, derives = _corpus(tmp_path), tmp_path / "derives"

    def convertir(chemin: Path) -> str:
        if chemin.suffix == ".docx":
            raise ValueError("document corrompu")
        return "contenu"

    resultats = parser_lot(
        [("alpha/spec.docx", "a" * 64), ("alpha/guide.pdf", "b" * 64)],
        racine,
        derives,
        convertir=convertir,
        pdf_sans_texte=lambda _: False,
    )
    par_chemin = {r.chemin: r for r in resultats}
    assert par_chemin["alpha/spec.docx"].statut == "echec"
    assert "document corrompu" in par_chemin["alpha/spec.docx"].erreur
    assert par_chemin["alpha/guide.pdf"].statut == "parse"  # le lot a continué


def test_pdf_scanne_marque_ocr_requis(tmp_path: Path) -> None:
    racine, derives = _corpus(tmp_path), tmp_path / "derives"
    resultats = parser_lot(
        [("alpha/guide.pdf", "b" * 64)],
        racine,
        derives,
        convertir=lambda _: pytest.fail("un PDF sans texte ne doit pas être converti"),
        pdf_sans_texte=lambda _: True,
    )
    assert resultats[0].statut == "ocr_requis"
    assert resultats[0].chemin_derive is None


def test_reprise_sur_hash_ne_reconvertit_pas(tmp_path: Path) -> None:
    racine, derives = _corpus(tmp_path), tmp_path / "derives"
    derives.mkdir()
    (derives / ("a" * 64 + ".md")).write_text("déjà converti", encoding="utf-8")
    appels = []
    resultats = parser_lot(
        [("alpha/spec.docx", "a" * 64)],
        racine,
        derives,
        convertir=lambda chemin: appels.append(chemin) or "jamais",
        pdf_sans_texte=lambda _: False,
    )
    assert resultats[0].statut == "inchange"
    assert appels == []  # aucune conversion : le dérivé du sha256 existe (D9)


def _ecrire_eml(tmp_path: Path, corps_html_seul: bool = False) -> Path:
    """Courriel de test réaliste (stdlib) : en-têtes, corps, pièce jointe."""
    from email.message import EmailMessage

    message = EmailMessage()
    message["Subject"] = "Validation du périmètre RGPD"
    message["From"] = "po@exemple.gouv.fr"
    message["To"] = "referent@exemple.gouv.fr"
    message["Date"] = "Mon, 06 Jul 2026 10:00:00 +0200"
    if corps_html_seul:
        message.add_alternative("<p>Bonjour, le <b>périmètre</b> est validé.</p>", subtype="html")
    else:
        message.set_content("Bonjour,\nle périmètre est validé.")
    message.add_attachment(
        b"%PDF-fictif", maintype="application", subtype="pdf", filename="annexe-rgpd.pdf"
    )
    chemin = tmp_path / "echange.eml"
    chemin.write_bytes(message.as_bytes())
    return chemin


def test_conversion_eml_entetes_corps_et_pieces_jointes(tmp_path: Path) -> None:
    markdown = convertir_eml_en_markdown(_ecrire_eml(tmp_path))
    assert markdown.startswith("# Validation du périmètre RGPD")
    assert "- **From** : po@exemple.gouv.fr" in markdown
    assert "- **Date** : Mon, 06 Jul 2026 10:00:00 +0200" in markdown
    assert "le périmètre est validé" in markdown
    # La pièce jointe est LISTÉE, jamais extraite (elle se dépose à part).
    assert "## Pièces jointes (non extraites)" in markdown
    assert "- annexe-rgpd.pdf" in markdown
    assert "%PDF" not in markdown


def test_conversion_eml_html_seul_degrade_en_texte(tmp_path: Path) -> None:
    markdown = convertir_eml_en_markdown(_ecrire_eml(tmp_path, corps_html_seul=True))
    assert "périmètre" in markdown
    assert "<p>" not in markdown and "<b>" not in markdown


def test_routage_eml_ne_passe_pas_par_docling(tmp_path: Path) -> None:
    racine = tmp_path / "corpus"
    (racine / "alpha").mkdir(parents=True)
    _ecrire_eml(racine / "alpha")
    resultats = parser_lot(
        [("alpha/echange.eml", "c" * 64)],
        racine,
        tmp_path / "derives",
        convertir=lambda _: pytest.fail("un .eml ne doit jamais passer par docling"),
        pdf_sans_texte=lambda _: False,
    )
    assert resultats[0].statut == "parse"
    derive = Path(resultats[0].chemin_derive).read_text(encoding="utf-8")
    assert derive.startswith("# Validation du périmètre RGPD")


def test_detection_pdf_sans_texte_sur_fixtures_reelles() -> None:
    # pypdf réel sur les fixtures du repo : natif = texte, scanné = aucun texte.
    assert est_pdf_sans_texte(FIXTURES / "projet-beta" / "scan-courrier-prefecture.pdf") is True
    assert est_pdf_sans_texte(FIXTURES / "projet-beta" / "guide-installation.pdf") is False


class FauxCurseur:
    def __init__(self, lignes: list[tuple[str, str]]) -> None:
        self.lignes = lignes
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict) -> None:
        self.requetes.append((requete, parametres))

    def fetchall(self) -> list[tuple[str, str]]:
        return self.lignes

    def __enter__(self) -> "FauxCurseur":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, lignes: list[tuple[str, str]] | None = None) -> None:
        self.curseur = FauxCurseur(lignes or [])
        self.commits = 0

    def cursor(self) -> FauxCurseur:
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


def test_lecture_filtre_docx_et_pdf() -> None:
    connexion = FausseConnexion([("a.docx", "a" * 64)])
    assert lire_documents_a_parser(connexion) == [("a.docx", "a" * 64)]
    requete, parametres = connexion.curseur.requetes[0]
    assert "extension = ANY" in requete
    assert parametres["extensions"] == list(EXTENSIONS_PARSEES)


def test_enregistrement_statuts_inchange_persiste_comme_parse() -> None:
    connexion = FausseConnexion()
    enregistrer_resultats(
        connexion,
        [
            ResultatParsing("a.docx", "inchange", "derived/md/aa.md"),
            ResultatParsing("b.pdf", "echec", None, "ValueError: cassé"),
        ],
    )
    statuts = [p["statut"] for _, p in connexion.curseur.requetes]
    assert statuts == ["parse", "echec"]
    assert connexion.commits == 1


def test_rapport_csv(tmp_path: Path) -> None:
    chemin = tmp_path / "rapport.csv"
    ecrire_rapport(
        [
            ResultatParsing("a.docx", "parse", "derived/md/aa.md"),
            ResultatParsing("b.pdf", "echec", None, "ValueError: cassé"),
        ],
        chemin,
    )
    lignes = list(csv.DictReader(chemin.open(encoding="utf-8")))
    assert lignes[1]["statut"] == "echec"
    assert "cassé" in lignes[1]["erreur"]


def test_main_exige_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main(["--corpus", "evals/fixtures"]) == 2
    assert "DATABASE_URL absente" in capsys.readouterr().err
