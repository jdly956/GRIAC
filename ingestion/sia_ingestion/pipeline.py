"""Orchestrateur du pipeline complet — S3.10 : « Indexer maintenant » depuis l'UI.

Lancé en arrière-plan par l'api (`POST /ingestion/lancer`) : enchaîne les
nœuds du DAG E1 (scan → parse → qualify → chunk → embed) sur le dossier
corpus et consigne l'avancement dans `ingestion_runs` (rapport JSONB mis à
jour après CHAQUE nœud — l'écran de suivi lit en direct). Politique d'échec :

- code 2 d'un nœud (config manquante, corpus introuvable) → arrêt, `echec` ;
- code 1 (échecs partiels : OCR requis, lot d'embeddings en 429) → on
  poursuit, statut final `echec_partiel` — la relance reprend sur hash (D9) ;
- exception imprévue → arrêt, `echec`, le message entre au rapport.
"""

import argparse
import json
import os
import sys

import psycopg

from sia_ingestion import chunk, embed, parse, qualify, scan

NOEUDS = ("scan", "parse", "qualify", "chunk", "embed")


def _lancer_noeud(nom: str, corpus: str) -> int:
    if nom == "scan":
        return scan.main(["--corpus", corpus])
    if nom == "parse":
        return parse.main(["--corpus", corpus])
    if nom == "qualify":
        return qualify.main([])
    if nom == "chunk":
        return chunk.main([])
    return embed.main([])


def _maj_run(connexion, run_id: int, statut: str, rapport: dict, fin: bool = False) -> None:
    with connexion.cursor() as curseur:
        curseur.execute(
            "UPDATE ingestion_runs SET statut = %(statut)s, rapport = %(rapport)s"
            + (", termine_le = now()" if fin else "")
            + " WHERE id = %(id)s",
            {"id": run_id, "statut": statut, "rapport": json.dumps(rapport)},
        )
    connexion.commit()


def executer_run(connexion, run_id: int, corpus: str, lancer_noeud=_lancer_noeud) -> str:
    """Enchaîne les nœuds, rapporte au fil de l'eau ; renvoie le statut final."""
    rapport: dict[str, str] = {}
    statut_final = "termine"
    for nom in NOEUDS:
        try:
            code = lancer_noeud(nom, corpus)
        except Exception as exc:  # un nœud qui explose n'emporte pas le run muet
            rapport[nom] = f"echec ({type(exc).__name__}: {exc})"
            _maj_run(connexion, run_id, "echec", rapport, fin=True)
            return "echec"
        if code == 0:
            rapport[nom] = "ok"
        elif code == 1:
            rapport[nom] = "echecs partiels — relance possible (reprise sur hash, D9)"
            statut_final = "echec_partiel"
        else:
            rapport[nom] = f"echec (code {code})"
            _maj_run(connexion, run_id, "echec", rapport, fin=True)
            return "echec"
        _maj_run(connexion, run_id, "en_cours", rapport)
    _maj_run(connexion, run_id, statut_final, rapport, fin=True)
    return statut_final


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Pipeline d'ingestion complet (S3.10)")
    parseur.add_argument("--corpus", required=True)
    parseur.add_argument("--run-id", type=int, required=True)
    arguments = parseur.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL absente : le pipeline écrit son suivi en base.", file=sys.stderr)
        return 2
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(database_url) as connexion:
        statut = executer_run(connexion, arguments.run_id, arguments.corpus)
    return 0 if statut == "termine" else 1


if __name__ == "__main__":
    raise SystemExit(main())
