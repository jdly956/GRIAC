"""Nœud E du DAG d'ingestion (E1) : embeddings bge-m3 par lots -> pgvector.

`make ingest-embed` : vectorise les chunks sans embedding (reprise naturelle :
une relance ne retraite que les `embedding IS NULL`, y compris après un échec
de lot — c'est aussi le mécanisme des « embeddings de nuit » si les quotas
l'imposent, D9). Client Albert de S1.5 (Settings S1.4, clé jamais loguée),
alias `openweight-embeddings` (bge-m3, dimension 1024), lots de 32 par défaut,
**`encoding_format="float"` obligatoire** (le défaut base64 du SDK rend un 500
sur Albert — constaté sur pod, S1.5). Un lot en échec n'interrompt pas les
suivants ; le vecteur est écrit via un cast `::vector` (aucune dépendance
pgvector côté Python).
"""

import argparse
import os
import sys

import psycopg

from sia_api.albert import creer_client
from sia_api.config import charger_settings

TAILLE_LOT_PAR_DEFAUT = 32
DIMENSION_ATTENDUE = 1024  # bge-m3 (relevé make probe, S1.5)

REQUETE_A_VECTORISER = "SELECT id, contenu FROM chunks WHERE embedding IS NULL ORDER BY id"
REQUETE_MAJ = "UPDATE chunks SET embedding = %(vecteur)s::vector WHERE id = %(id)s"


def formater_vecteur(valeurs: list[float]) -> str:
    return "[" + ",".join(repr(valeur) for valeur in valeurs) + "]"


def lire_chunks_a_vectoriser(connexion) -> list[tuple[int, str]]:
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_A_VECTORISER)
        return [(ligne[0], ligne[1]) for ligne in curseur.fetchall()]


def vectoriser_lot(client, settings, contenus: list[str]) -> tuple[list[list[float]], int]:
    """Vecteurs du lot + tokens consommés (S3.11 — 0 si l'API n'en renvoie pas)."""
    reponse = client.embeddings.create(
        model=settings.albert_model_embeddings,
        input=contenus,
        encoding_format="float",  # gotcha Albert (S1.5) : jamais le base64 par défaut
    )
    donnees = sorted(reponse.data, key=lambda element: element.index)
    usage = getattr(reponse, "usage", None)
    tokens = (
        (getattr(usage, "total_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0)
        if usage
        else 0
    )
    return [element.embedding for element in donnees], tokens


def traiter_chunks(
    connexion, client, settings, taille_lot: int = TAILLE_LOT_PAR_DEFAUT
) -> dict[str, int]:
    """Vectorise par lots ; un lot en échec est signalé et n'interrompt pas la suite."""
    chunks = lire_chunks_a_vectoriser(connexion)
    statistiques = {"vectorises": 0, "lots": 0, "lots_en_echec": 0, "tokens": 0}
    for depart in range(0, len(chunks), taille_lot):
        lot = chunks[depart : depart + taille_lot]
        statistiques["lots"] += 1
        try:
            vecteurs, tokens_lot = vectoriser_lot(client, settings, [contenu for _, contenu in lot])
        except Exception as exc:  # réseau/quota : lot isolé, relance possible
            print(
                f"  lot en échec (chunks {lot[0][0]}–{lot[-1][0]}) : {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            statistiques["lots_en_echec"] += 1
            continue
        if vecteurs and len(vecteurs[0]) != DIMENSION_ATTENDUE:
            print(
                f"  avertissement : dimension {len(vecteurs[0])} ≠ {DIMENSION_ATTENDUE} attendue",
                file=sys.stderr,
            )
        with connexion.cursor() as curseur:
            for (identifiant, _), vecteur in zip(lot, vecteurs, strict=True):
                curseur.execute(
                    REQUETE_MAJ, {"id": identifiant, "vecteur": formater_vecteur(vecteur)}
                )
            if tokens_lot:
                # S3.11 : la conso embeddings entre au registre (jauge tpd).
                curseur.execute(
                    "INSERT INTO conso_tokens (source, modele, tokens_entree) "
                    "VALUES ('embeddings', %(modele)s, %(tokens)s)",
                    {"modele": settings.albert_model_embeddings, "tokens": tokens_lot},
                )
        connexion.commit()  # commit par lot : un échec ultérieur ne perd pas l'acquis
        statistiques["vectorises"] += len(lot)
        statistiques["tokens"] += tokens_lot
    return statistiques


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Embeddings des chunks -> pgvector")
    parseur.add_argument("--lot", type=int, default=TAILLE_LOT_PAR_DEFAUT, help="taille de lot")
    arguments = parseur.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL absente : les embeddings lisent et mettent à jour la table chunks.",
            file=sys.stderr,
        )
        return 2
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    try:
        settings = charger_settings()
    except RuntimeError as erreur:
        print(str(erreur), file=sys.stderr)
        return 2
    client = creer_client(settings)

    with psycopg.connect(database_url) as connexion:
        statistiques = traiter_chunks(connexion, client, settings, arguments.lot)
    print(
        f"{statistiques['vectorises']} chunks vectorisés en {statistiques['lots']} lot(s), "
        f"{statistiques['lots_en_echec']} lot(s) en échec"
        + (" — relancer make ingest-embed pour reprendre" if statistiques["lots_en_echec"] else "")
    )
    return 1 if statistiques["lots_en_echec"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
