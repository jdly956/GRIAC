"""Nœud C du DAG d'ingestion (S1.9) : qualification v0 — métadonnées & versions.

`make ingest-qualify` : à partir du seul inventaire (aucun accès fichier), infère
pour chaque document — le projet (1er niveau du chemin, enregistré comme
**suggestion** `projet_suggere` : l'association faisant foi est confirmée par le
PO via S1.11, arbitrage A6), la date portée par le nom, les marqueurs de version
(`v\\d+`, `VF`, `final`), le statut brouillon (`draft`, `brouillon`, `WIP`).
Puis : doublons détectés par sha256 (`doublon_de` → chemin canonique) et versions
regroupées par similarité de nom (`groupe_version` = nom débarrassé des marqueurs),
la plus récente du groupe taguée `est_reference` — le filtre « statut = référence »
du RAG (E2) s'appuie dessus.

Règle de « plus récente » (documentée, ajustable) : non-brouillon d'abord, puis
numéro de version, puis marque finale (final/VF), puis date (nom sinon mtime).
Les doublons sont exclus du choix de la référence.
"""

import argparse
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath

import psycopg

MOTIF_VERSION = re.compile(r"(?<![a-z0-9])v(\d+)", re.IGNORECASE)
MOTIF_VF = re.compile(r"(?<![a-z0-9])vf\d*", re.IGNORECASE)
MOTIF_FINAL = re.compile(r"final", re.IGNORECASE)
MOTIF_BROUILLON = re.compile(r"draft|brouillon|wip", re.IGNORECASE)
MOTIF_COPIE = re.compile(r"copie|copy", re.IGNORECASE)
MOTIF_DATE_ISO = re.compile(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])")
MOTIF_DATE_FR = re.compile(r"(0[1-9]|[12]\d|3[01])[-_.](0[1-9]|1[0-2])[-_.](20\d{2})")

REQUETE_LECTURE = "SELECT chemin, nom, mtime, sha256 FROM documents ORDER BY chemin"

REQUETE_MAJ = """
    UPDATE documents
    SET projet_suggere = %(projet_suggere)s,
        date_nom = %(date_nom)s,
        version_no = %(version_no)s,
        marque_finale = %(marque_finale)s,
        statut_brouillon = %(statut_brouillon)s,
        groupe_version = %(groupe_version)s,
        est_reference = %(est_reference)s,
        doublon_de = %(doublon_de)s
    WHERE chemin = %(chemin)s
"""


@dataclass(frozen=True)
class LigneDocument:
    chemin: str
    nom: str
    mtime: str  # ISO 8601
    sha256: str


@dataclass
class Qualification:
    chemin: str
    projet_suggere: str | None
    date_nom: date | None
    version_no: int | None
    marque_finale: bool
    statut_brouillon: bool
    groupe_version: str
    est_reference: bool = False
    doublon_de: str | None = None


def extraire_date_nom(nom: str) -> date | None:
    """Date portée par le nom de fichier — ISO (2026-06-15, 20260615) ou FR (15-06-2026)."""
    correspondance = MOTIF_DATE_ISO.search(nom)
    if correspondance:
        annee, mois, jour = correspondance.groups()
        return date(int(annee), int(mois), int(jour))
    correspondance = MOTIF_DATE_FR.search(nom)
    if correspondance:
        jour, mois, annee = correspondance.groups()
        return date(int(annee), int(mois), int(jour))
    return None


def normaliser_groupe(nom: str) -> str:
    """Clé de regroupement des versions : nom sans extension, accents, marqueurs ni dates."""
    base = PurePosixPath(nom).stem
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = MOTIF_DATE_ISO.sub(" ", base)
    base = MOTIF_DATE_FR.sub(" ", base)
    base = MOTIF_VF.sub(" ", base)
    base = MOTIF_VERSION.sub(" ", base)
    base = MOTIF_FINAL.sub(" ", base)
    base = MOTIF_BROUILLON.sub(" ", base)
    base = MOTIF_COPIE.sub(" ", base)
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return base


def qualifier_document(ligne: LigneDocument) -> Qualification:
    chemin = PurePosixPath(ligne.chemin)
    version = MOTIF_VERSION.search(ligne.nom)
    return Qualification(
        chemin=ligne.chemin,
        projet_suggere=chemin.parts[0] if len(chemin.parts) > 1 else None,
        date_nom=extraire_date_nom(ligne.nom),
        version_no=int(version.group(1)) if version else None,
        marque_finale=bool(MOTIF_FINAL.search(ligne.nom) or MOTIF_VF.search(ligne.nom)),
        statut_brouillon=bool(MOTIF_BROUILLON.search(ligne.nom)),
        groupe_version=normaliser_groupe(ligne.nom),
    )


def _date_effective(qualification: Qualification, ligne: LigneDocument) -> str:
    if qualification.date_nom:
        return qualification.date_nom.isoformat()
    return ligne.mtime


def marquer_doublons(lignes: list[LigneDocument], qualifications: dict[str, Qualification]) -> None:
    """Doublons par sha256 : le canonique est un non-« copie » (sinon chemin le plus court)."""
    par_hash: dict[str, list[LigneDocument]] = {}
    for ligne in lignes:
        par_hash.setdefault(ligne.sha256, []).append(ligne)
    for groupe in par_hash.values():
        if len(groupe) < 2:
            continue
        canonique = min(
            groupe,
            key=lambda ligne: (
                bool(MOTIF_COPIE.search(ligne.nom)),
                len(ligne.chemin),
                ligne.chemin,
            ),
        )
        for ligne in groupe:
            if ligne.chemin != canonique.chemin:
                qualifications[ligne.chemin].doublon_de = canonique.chemin


def marquer_references(
    lignes: list[LigneDocument], qualifications: dict[str, Qualification]
) -> None:
    """Dans chaque groupe (projet, groupe_version), la plus récente devient la référence."""
    par_ligne = {ligne.chemin: ligne for ligne in lignes}
    groupes: dict[tuple[str | None, str], list[Qualification]] = {}
    for qualification in qualifications.values():
        if qualification.doublon_de:  # un doublon n'est jamais la référence
            continue
        cle = (qualification.projet_suggere, qualification.groupe_version)
        groupes.setdefault(cle, []).append(qualification)
    for membres in groupes.values():
        reference = max(
            membres,
            key=lambda q: (
                not q.statut_brouillon,
                q.version_no or 0,
                q.marque_finale,
                _date_effective(q, par_ligne[q.chemin]),
                q.chemin,
            ),
        )
        reference.est_reference = True


def qualifier_lot(lignes: list[LigneDocument]) -> list[Qualification]:
    """Qualification complète d'un inventaire — fonction pure, sans DB ni fichiers."""
    qualifications = {ligne.chemin: qualifier_document(ligne) for ligne in lignes}
    marquer_doublons(lignes, qualifications)
    marquer_references(lignes, qualifications)
    return [qualifications[ligne.chemin] for ligne in lignes]


def lire_inventaire(connexion) -> list[LigneDocument]:
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_LECTURE)
        return [
            LigneDocument(chemin=ligne[0], nom=ligne[1], mtime=str(ligne[2]), sha256=ligne[3])
            for ligne in curseur.fetchall()
        ]


def enregistrer_qualifications(connexion, qualifications: list[Qualification]) -> None:
    with connexion.cursor() as curseur:
        for qualification in qualifications:
            curseur.execute(
                REQUETE_MAJ,
                {
                    "chemin": qualification.chemin,
                    "projet_suggere": qualification.projet_suggere,
                    "date_nom": qualification.date_nom,
                    "version_no": qualification.version_no,
                    "marque_finale": qualification.marque_finale,
                    "statut_brouillon": qualification.statut_brouillon,
                    "groupe_version": qualification.groupe_version,
                    "est_reference": qualification.est_reference,
                    "doublon_de": qualification.doublon_de,
                },
            )
    connexion.commit()


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        description="Qualification v0 : métadonnées, doublons, versions -> table documents"
    ).parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL absente : la qualification lit et met à jour la table documents. "
            "Exemple : postgresql+psycopg://sia:sia_dev@localhost:5432/sia — jamais en dur.",
            file=sys.stderr,
        )
        return 2
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(database_url) as connexion:
        lignes = lire_inventaire(connexion)
        qualifications = qualifier_lot(lignes)
        enregistrer_qualifications(connexion, qualifications)

    nb_references = sum(1 for q in qualifications if q.est_reference)
    nb_doublons = sum(1 for q in qualifications if q.doublon_de)
    nb_brouillons = sum(1 for q in qualifications if q.statut_brouillon)
    print(
        f"{len(qualifications)} documents qualifiés — {nb_references} références, "
        f"{nb_doublons} doublons, {nb_brouillons} brouillons. "
        "NB : projet_suggere est une suggestion (A6) — confirmation PO via S1.11."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
