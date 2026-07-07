"""Nœud B du DAG d'ingestion (S1.8) : parsing docling -> markdown structuré.

`make ingest-parse CORPUS=<dossier>` : pour chaque document parsable inventorié
par le scan (S1.7) — docx, pdf, et depuis S3.16 pptx, xlsx, eml —, convertit en
markdown (hiérarchie de titres préservée, tableaux rendus en tableaux markdown
— jamais détruits) et écrit le dérivé `derived/md/<sha256>.md` (hors repo).
Reprise sur hash (D9) : un dérivé déjà présent pour le sha256 courant n'est pas
reconverti. Les PDF sans couche texte sont marqués `ocr_requis`. Un document en
échec n'interrompt pas le lot : statut `echec` en base, rapport CSV.

docling (docx/pdf/pptx/xlsx) est importé paresseusement (torch, lourd) : les TU
injectent un faux convertisseur et ne le chargent jamais. Les `.eml` passent
par un convertisseur dédié (stdlib `email`) — docling ne les couvre pas.
"""

import argparse
import csv
import os
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psycopg

from sia_api.documents import EXTENSIONS_PARSABLES

DERIVES_PAR_DEFAUT = "derived/md"
RAPPORT_PAR_DEFAUT = "derived/rapport-parsing.csv"
EXTENSIONS_PARSEES = EXTENSIONS_PARSABLES  # source unique : sia_api.documents (S3.16)

REQUETE_A_PARSER = """
    SELECT chemin, sha256 FROM documents
    WHERE extension = ANY(%(extensions)s)
    ORDER BY chemin
"""

REQUETE_MAJ_STATUT = """
    UPDATE documents
    SET statut_parsing = %(statut)s,
        chemin_derive = %(chemin_derive)s,
        erreur_parsing = %(erreur)s,
        date_parsing = now()
    WHERE chemin = %(chemin)s
"""


@dataclass(frozen=True)
class ResultatParsing:
    chemin: str
    statut: str  # parse | inchange | ocr_requis | echec
    chemin_derive: str | None = None
    erreur: str | None = None


_convertisseur = None


def convertir_en_markdown(chemin: Path) -> str:
    """Conversion docling -> markdown. Le convertisseur est construit une seule fois.

    OCR désactivé : les PDF sans couche texte sont déroutés en `ocr_requis`
    AVANT docling (l'OCR est au sprint 2) — inutile donc de télécharger les
    modèles OCR, seuls layout/tableaux servent aux PDF natifs.
    """
    global _convertisseur
    if _convertisseur is None:
        # Import paresseux : docling charge torch et ses modèles.
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options_pdf = PdfPipelineOptions(do_ocr=False)
        _convertisseur = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options_pdf)}
        )
    return _convertisseur.convert(chemin).document.export_to_markdown()


def convertir_eml_en_markdown(chemin: Path) -> str:
    """Courriel .eml -> markdown (S3.16) — docling ne couvre pas ce format.

    En-têtes utiles en tête (le RAG y trouve dates et interlocuteurs), corps
    en texte (le HTML seul est dégradé en texte brut), pièces jointes LISTÉES
    mais jamais extraites — un PJ pertinente se dépose comme document à part.
    """
    import re as _re
    from email import policy
    from email.parser import BytesParser

    message = BytesParser(policy=policy.default).parse(chemin.open("rb"))
    lignes = [f"# {message.get('Subject', '(sans objet)')}", ""]
    for entete in ("From", "To", "Cc", "Date"):
        if message.get(entete):
            lignes.append(f"- **{entete}** : {message.get(entete)}")
    lignes.append("")

    corps = message.get_body(preferencelist=("plain", "html"))
    texte = corps.get_content() if corps is not None else ""
    if corps is not None and corps.get_content_type() == "text/html":
        texte = _re.sub(r"<[^>]+>", " ", texte)  # dégradé assumé : texte brut
    lignes.append(texte.strip())

    pieces = [piece.get_filename() for piece in message.iter_attachments() if piece.get_filename()]
    if pieces:
        lignes += ["", "## Pièces jointes (non extraites)", ""]
        lignes += [f"- {nom}" for nom in pieces]
    return "\n".join(lignes)


def est_pdf_sans_texte(chemin: Path) -> bool:
    """PDF « scanné » : aucune page ne porte de texte extractible."""
    from pypdf import PdfReader

    lecteur = PdfReader(chemin)
    return all(not (page.extract_text() or "").strip() for page in lecteur.pages)


def parser_lot(
    lignes: list[tuple[str, str]],
    racine: Path,
    dossier_derives: Path,
    convertir: Callable[[Path], str] = convertir_en_markdown,
    pdf_sans_texte: Callable[[Path], bool] = est_pdf_sans_texte,
) -> list[ResultatParsing]:
    """Parse chaque (chemin, sha256) ; une erreur n'interrompt jamais le lot (CA3)."""
    resultats = []
    for chemin_relatif, sha256 in lignes:
        source = racine / chemin_relatif
        derive = dossier_derives / f"{sha256}.md"
        try:
            if derive.exists():
                # Reprise sur hash (D9) : contenu identique déjà converti
                # (couvre aussi les doublons byte-à-byte : un seul dérivé).
                resultats.append(ResultatParsing(chemin_relatif, "inchange", str(derive)))
            elif source.suffix.lower() == ".pdf" and pdf_sans_texte(source):
                resultats.append(ResultatParsing(chemin_relatif, "ocr_requis"))
            else:
                # S3.16 : les .eml ont leur convertisseur dédié (stdlib) ; le
                # reste (docx/pdf/pptx/xlsx) passe par docling.
                if source.suffix.lower() == ".eml":
                    markdown = convertir_eml_en_markdown(source)
                else:
                    markdown = convertir(source)
                dossier_derives.mkdir(parents=True, exist_ok=True)
                derive.write_text(markdown, encoding="utf-8")
                resultats.append(ResultatParsing(chemin_relatif, "parse", str(derive)))
        except Exception as exc:  # échec isolé : statut en base, lot poursuivi
            resultats.append(
                ResultatParsing(chemin_relatif, "echec", None, f"{type(exc).__name__}: {exc}")
            )
    return resultats


def lire_documents_a_parser(connexion) -> list[tuple[str, str]]:
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_A_PARSER, {"extensions": list(EXTENSIONS_PARSEES)})
        return [(ligne[0], ligne[1]) for ligne in curseur.fetchall()]


def enregistrer_resultats(connexion, resultats: list[ResultatParsing]) -> None:
    """`inchange` est persisté comme `parse` : le dérivé existe et est à jour."""
    with connexion.cursor() as curseur:
        for resultat in resultats:
            curseur.execute(
                REQUETE_MAJ_STATUT,
                {
                    "chemin": resultat.chemin,
                    "statut": "parse" if resultat.statut == "inchange" else resultat.statut,
                    "chemin_derive": resultat.chemin_derive,
                    "erreur": resultat.erreur,
                },
            )
    connexion.commit()


def ecrire_rapport(resultats: list[ResultatParsing], chemin_rapport: Path) -> None:
    chemin_rapport.parent.mkdir(parents=True, exist_ok=True)
    with chemin_rapport.open("w", newline="", encoding="utf-8") as flux:
        ecrivain = csv.writer(flux)
        ecrivain.writerow(["chemin", "statut", "chemin_derive", "erreur"])
        for resultat in resultats:
            ecrivain.writerow(
                [resultat.chemin, resultat.statut, resultat.chemin_derive, resultat.erreur]
            )


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Parsing docling -> dérivés markdown")
    parseur.add_argument("--corpus", required=True, help="dossier racine du corpus (cf. scan)")
    parseur.add_argument("--derives", default=DERIVES_PAR_DEFAUT, help="dossier des dérivés .md")
    parseur.add_argument("--rapport", default=RAPPORT_PAR_DEFAUT, help="rapport CSV du lot")
    args = parseur.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL absente : le parsing lit et met à jour la table documents. "
            "Exemple : postgresql+psycopg://sia:sia_dev@localhost:5432/sia — jamais en dur.",
            file=sys.stderr,
        )
        return 2
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(database_url) as connexion:
        lignes = lire_documents_a_parser(connexion)
        resultats = parser_lot(lignes, Path(args.corpus), Path(args.derives))
        enregistrer_resultats(connexion, resultats)

    ecrire_rapport(resultats, Path(args.rapport))
    compteurs = Counter(resultat.statut for resultat in resultats)
    print(
        f"{len(resultats)} documents — {compteurs['parse']} parsés, "
        f"{compteurs['inchange']} inchangés (reprise sur hash), "
        f"{compteurs['ocr_requis']} ocr_requis, {compteurs['echec']} échecs ; "
        f"rapport : {args.rapport}"
    )
    for resultat in resultats:
        if resultat.statut == "echec":
            print(f"  échec — {resultat.chemin} : {resultat.erreur}", file=sys.stderr)
    return 1 if compteurs["echec"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
