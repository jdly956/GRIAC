"""Nœud A du DAG d'ingestion (S1.7) : scan du corpus & inventaire.

`make ingest-scan CORPUS=<dossier>` : parcours récursif d'un dossier local,
sha256, taille, extension, dates ; upsert en table `documents` (clé
d'idempotence : le chemin relatif — relance = zéro doublon, un fichier modifié
met à jour sa ligne) ; export CSV de l'inventaire. Les doublons de contenu
(même sha256 sous des chemins différents) restent des lignes distinctes :
leur détection est le travail de la qualification (S1.9). La reprise sur hash
(D9) s'appuiera sur sha256 pour ne re-traiter que les fichiers modifiés (S1.8+).

`s3://…` est refusé explicitement à ce stade : le snapshot MinIO n'existe pas
encore (prérequis note §7) ; la lecture S3 arrive avec le DAG conteneurisé (E1).
"""

import argparse
import csv
import hashlib
import os
import sys
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path

import psycopg

CSV_PAR_DEFAUT = "derived/inventaire.csv"


@dataclass(frozen=True)
class FichierInventorie:
    chemin: str  # relatif à la racine du corpus, séparateur POSIX
    nom: str
    extension: str  # sans le point, en minuscules ; "" si aucune
    taille_octets: int
    sha256: str
    mtime: str  # ISO 8601, UTC


def calculer_sha256(chemin: Path) -> str:
    empreinte = hashlib.sha256()
    with chemin.open("rb") as flux:
        for bloc in iter(lambda: flux.read(1024 * 1024), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


def scanner_dossier(racine: Path) -> list[FichierInventorie]:
    """Parcours récursif trié ; fichiers et dossiers cachés (.*) ignorés."""
    if not racine.is_dir():
        raise NotADirectoryError(f"Corpus introuvable : {racine} n'est pas un dossier accessible.")
    inventaire = []
    for chemin in sorted(racine.rglob("*")):
        if not chemin.is_file():
            continue
        relatif = chemin.relative_to(racine)
        if any(partie.startswith(".") for partie in relatif.parts):
            continue
        stat = chemin.stat()
        inventaire.append(
            FichierInventorie(
                chemin=relatif.as_posix(),
                nom=chemin.name,
                extension=chemin.suffix.lstrip(".").lower(),
                taille_octets=stat.st_size,
                sha256=calculer_sha256(chemin),
                mtime=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            )
        )
    return inventaire


# `xmax = 0` : la ligne vient d'être insérée (idiome PostgreSQL pour distinguer
# insertion et mise à jour au retour d'un ON CONFLICT DO UPDATE).
REQUETE_UPSERT = """
    INSERT INTO documents (chemin, nom, extension, taille_octets, sha256, mtime)
    VALUES (%(chemin)s, %(nom)s, %(extension)s, %(taille_octets)s, %(sha256)s, %(mtime)s)
    ON CONFLICT (chemin) DO UPDATE SET
        nom = EXCLUDED.nom,
        extension = EXCLUDED.extension,
        taille_octets = EXCLUDED.taille_octets,
        sha256 = EXCLUDED.sha256,
        mtime = EXCLUDED.mtime,
        derniere_vue = now()
    RETURNING (xmax = 0) AS insere
"""


def upserter_documents(connexion, fichiers: list[FichierInventorie]) -> dict[str, int]:
    """Upsert de l'inventaire ; retourne les compteurs insérés / mis à jour."""
    statistiques = {"inseres": 0, "mis_a_jour": 0}
    with connexion.cursor() as curseur:
        for fichier in fichiers:
            curseur.execute(REQUETE_UPSERT, asdict(fichier))
            insere = curseur.fetchone()[0]
            statistiques["inseres" if insere else "mis_a_jour"] += 1
    connexion.commit()
    return statistiques


def exporter_csv(fichiers: list[FichierInventorie], chemin_csv: Path) -> None:
    chemin_csv.parent.mkdir(parents=True, exist_ok=True)
    with chemin_csv.open("w", newline="", encoding="utf-8") as flux:
        ecrivain = csv.DictWriter(flux, fieldnames=[f.name for f in fields(FichierInventorie)])
        ecrivain.writeheader()
        for fichier in fichiers:
            ecrivain.writerow(asdict(fichier))


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Scan du corpus -> table documents + CSV")
    parseur.add_argument("--corpus", required=True, help="dossier racine du corpus à scanner")
    parseur.add_argument("--csv", default=CSV_PAR_DEFAUT, help="chemin du CSV d'inventaire")
    args = parseur.parse_args(argv)

    if str(args.corpus).startswith("s3://"):
        print(
            "s3:// non pris en charge à ce stade : le snapshot MinIO n'existe pas encore "
            "(prérequis note §7) — utiliser un dossier local. La lecture S3 arrive avec E1.",
            file=sys.stderr,
        )
        return 2

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL absente : le scan écrit dans PostgreSQL (table documents). "
            "Exemple : postgresql+psycopg://sia:sia_dev@localhost:5432/sia — jamais en dur.",
            file=sys.stderr,
        )
        return 2
    # Les URL SQLAlchemy du compose (postgresql+psycopg://) sont acceptées telles quelles.
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    fichiers = scanner_dossier(Path(args.corpus))
    with psycopg.connect(database_url) as connexion:
        statistiques = upserter_documents(connexion, fichiers)
    exporter_csv(fichiers, Path(args.csv))
    print(
        f"{len(fichiers)} fichiers scannés — {statistiques['inseres']} insérés, "
        f"{statistiques['mis_a_jour']} mis à jour ; inventaire : {args.csv}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
