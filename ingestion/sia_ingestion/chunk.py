"""Nœud D du DAG d'ingestion (E1) : chunking des dérivés markdown.

`make ingest-chunk` : découpe chaque dérivé `derived/md/<sha256>.md` (documents
au statut `parse`) en chunks par sections de titres, budget **500–800 tokens**
avec chevauchement. Règle tableaux amendée (S3.19, session réelle 12) : on ne
coupe **jamais une ligne de tableau ni ne la sépare de son en-tête**, mais un
tableau au-delà du budget est **scindé par groupes de lignes, l'en-tête répété**
— un classeur Excel entier produisait sinon UN chunk de ~940k caractères qui
traversait E2 et explosait le budget de contexte. Les lignes de tableau sont
aussi compactées (docling padde chaque cellule à largeur fixe : ~75 % d'espaces
sur le xlsx de la session 12). Chunks écrits en table `chunks` avec le fil de
titres (`section`) pour la traçabilité des citations (E2). Reprise sur hash
(D9) : des chunks déjà présents pour le sha256 courant ne sont pas recalculés ;
un document modifié voit ses chunks remplacés. ⚠️ Corollaire : un changement
d'ALGORITHME de chunking ne re-chunke pas les documents en place — propagation
par suppression/redépôt du document (UI) ou purge de ses chunks.

Comptage de tokens : approximation `caractères / 4` (POC) — à recaler avec le
tokenizer réel de bge-m3 si l'éval E6 montre un écart significatif ; la fenêtre
bge-m3 relevée par `make probe` est de 8192, très au-dessus du budget.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

TOKENS_CIBLE_MIN = 500
TOKENS_MAX = 800
TOKENS_CHEVAUCHEMENT_MAX = 150

REQUETE_DOCUMENTS = """
    SELECT chemin, sha256, chemin_derive FROM documents
    WHERE statut_parsing = 'parse' AND chemin_derive IS NOT NULL
    ORDER BY chemin
"""
REQUETE_CHUNKS_EXISTANTS = """
    SELECT count(*) FROM chunks
    WHERE document_chemin = %(chemin)s AND sha256_document = %(sha256)s
"""
REQUETE_PURGE = "DELETE FROM chunks WHERE document_chemin = %(chemin)s"
REQUETE_INSERT = """
    INSERT INTO chunks (document_chemin, sha256_document, ordinal, section, contenu, nb_tokens)
    VALUES (%(chemin)s, %(sha256)s, %(ordinal)s, %(section)s, %(contenu)s, %(nb_tokens)s)
"""


@dataclass(frozen=True)
class Bloc:
    section: str  # fil de titres : « Titre > Sous-titre »
    contenu: str
    est_tableau: bool


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    section: str
    contenu: str
    nb_tokens: int


def estimer_tokens(texte: str) -> int:
    return max(1, len(texte) // 4)


def decouper_en_blocs(markdown: str) -> list[Bloc]:
    """Blocs atomiques : paragraphes et tableaux entiers, sous leur fil de titres."""
    blocs: list[Bloc] = []
    pile_titres: list[tuple[int, str]] = []
    paragraphe: list[str] = []
    tableau: list[str] = []

    def fil() -> str:
        return " > ".join(titre for _, titre in pile_titres)

    def clore_paragraphe() -> None:
        if paragraphe:
            blocs.append(Bloc(fil(), "\n".join(paragraphe).strip(), est_tableau=False))
            paragraphe.clear()

    def clore_tableau() -> None:
        if tableau:
            blocs.append(Bloc(fil(), "\n".join(tableau).strip(), est_tableau=True))
            tableau.clear()

    for ligne in markdown.splitlines():
        depouillee = ligne.strip()
        if depouillee.startswith("|"):
            clore_paragraphe()
            tableau.append(_compacter_ligne_tableau(ligne))
            continue
        clore_tableau()
        if depouillee.startswith("#"):
            clore_paragraphe()
            niveau = len(depouillee) - len(depouillee.lstrip("#"))
            titre = depouillee.lstrip("#").strip()
            while pile_titres and pile_titres[-1][0] >= niveau:
                pile_titres.pop()
            pile_titres.append((niveau, titre))
        elif not depouillee:
            clore_paragraphe()
        else:
            paragraphe.append(ligne)
    clore_paragraphe()
    clore_tableau()
    return [bloc for bloc in blocs if bloc.contenu]


_ESPACES_MULTIPLES = re.compile(r" {2,}")


def _compacter_ligne_tableau(ligne: str) -> str:
    """docling (xlsx surtout) padde chaque cellule à largeur fixe — les runs
    d'espaces sont du poids mort pour le budget ET pour bge-m3 (S3.19)."""
    return _ESPACES_MULTIPLES.sub(" ", ligne).rstrip()


def _scinder_tableau(bloc: Bloc) -> list[Bloc]:
    """Tableau au-delà du budget : scindé par GROUPES DE LIGNES, en-tête répété.

    L'esprit de la règle S1.8 est préservé : aucune ligne n'est coupée ni
    séparée de son en-tête — chaque morceau reste un tableau markdown complet
    et citable. Sans cela, un classeur Excel = un chunk de ~235k tokens
    (session 12) qui traversait l'assemblage E2.
    """
    lignes = bloc.contenu.splitlines()
    entete = lignes[:1]
    if len(lignes) > 1 and set(lignes[1].replace("|", "").strip()) <= set("-: "):
        entete = lignes[:2]  # ligne de titres + séparateur markdown
    morceaux: list[Bloc] = []
    courant = list(entete)
    for ligne in lignes[len(entete) :]:
        courant.append(ligne)
        if estimer_tokens("\n".join(courant)) >= TOKENS_MAX:
            morceaux.append(Bloc(bloc.section, "\n".join(courant), True))
            courant = list(entete)
    if len(courant) > len(entete):
        morceaux.append(Bloc(bloc.section, "\n".join(courant), True))
    return morceaux or [bloc]


def _scinder_bloc(bloc: Bloc) -> list[Bloc]:
    """Bloc au-dessus du budget : paragraphe scindé par lignes, tableau par
    groupes de lignes avec en-tête répété (S3.19) — jamais au milieu d'une ligne."""
    if estimer_tokens(bloc.contenu) <= TOKENS_MAX:
        return [bloc]
    if bloc.est_tableau:
        return _scinder_tableau(bloc)
    morceaux, courant = [], []
    for ligne in bloc.contenu.splitlines():
        courant.append(ligne)
        if estimer_tokens("\n".join(courant)) >= TOKENS_MAX:
            morceaux.append(Bloc(bloc.section, "\n".join(courant), False))
            courant = []
    if courant:
        morceaux.append(Bloc(bloc.section, "\n".join(courant), False))
    return morceaux


def assembler_chunks(blocs: list[Bloc]) -> list[Chunk]:
    """Assemblage glouton par section, budget 500–800 tokens, chevauchement d'un bloc."""
    chunks: list[Chunk] = []
    courant: list[Bloc] = []

    def emettre() -> None:
        if not courant:
            return
        contenu = "\n\n".join(bloc.contenu for bloc in courant)
        chunks.append(
            Chunk(
                ordinal=len(chunks),
                section=courant[0].section,
                contenu=contenu,
                nb_tokens=estimer_tokens(contenu),
            )
        )

    morceaux = [morceau for origine in blocs for morceau in _scinder_bloc(origine)]
    for bloc in morceaux:
        taille_courante = estimer_tokens("\n\n".join(b.contenu for b in courant)) if courant else 0
        changement_de_section = courant and bloc.section != courant[0].section
        deborde = courant and taille_courante + estimer_tokens(bloc.contenu) > TOKENS_MAX
        # On ne coupe sur un changement de section que si le chunk a déjà de la matière
        # (cible basse) — sinon les petites sections fusionnent pour éviter les miettes.
        if deborde or (changement_de_section and taille_courante >= TOKENS_CIBLE_MIN):
            dernier = courant[-1]
            emettre()
            courant = []
            # Chevauchement : le dernier bloc du chunk précédent ouvre le suivant
            # (jamais un tableau, jamais un bloc trop grand).
            if (
                not dernier.est_tableau
                and estimer_tokens(dernier.contenu) <= TOKENS_CHEVAUCHEMENT_MAX
                and not changement_de_section
            ):
                courant.append(dernier)
        courant.append(bloc)
    emettre()
    return chunks


def chunker_markdown(markdown: str) -> list[Chunk]:
    """Fonction pure : dérivé markdown -> chunks ordonnés."""
    return assembler_chunks(decouper_en_blocs(markdown))


def traiter_documents(connexion, racine: Path) -> dict[str, int]:
    """Chunking de tous les documents parsés ; reprise sur hash (D9)."""
    statistiques = {"documents": 0, "inchanges": 0, "chunks": 0, "echecs": 0}
    with connexion.cursor() as curseur:
        curseur.execute(REQUETE_DOCUMENTS)
        documents = curseur.fetchall()
        for chemin, sha256, chemin_derive in documents:
            curseur.execute(REQUETE_CHUNKS_EXISTANTS, {"chemin": chemin, "sha256": sha256})
            if curseur.fetchone()[0] > 0:
                statistiques["inchanges"] += 1
                continue
            derive = racine / chemin_derive
            try:
                chunks = chunker_markdown(derive.read_text(encoding="utf-8"))
            except OSError as erreur:
                print(f"  échec — {chemin} : {erreur}", file=sys.stderr)
                statistiques["echecs"] += 1
                continue
            curseur.execute(REQUETE_PURGE, {"chemin": chemin})
            for chunk in chunks:
                curseur.execute(
                    REQUETE_INSERT,
                    {
                        "chemin": chemin,
                        "sha256": sha256,
                        "ordinal": chunk.ordinal,
                        "section": chunk.section,
                        "contenu": chunk.contenu,
                        "nb_tokens": chunk.nb_tokens,
                    },
                )
            statistiques["documents"] += 1
            statistiques["chunks"] += len(chunks)
    connexion.commit()
    return statistiques


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Chunking des dérivés markdown -> table chunks")
    parseur.add_argument(
        "--racine", default=".", help="racine depuis laquelle résoudre chemin_derive"
    )
    arguments = parseur.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL absente : le chunking lit les documents parsés et écrit la table "
            "chunks. Exemple : postgresql+psycopg://sia:sia_dev@localhost:5432/sia.",
            file=sys.stderr,
        )
        return 2
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(database_url) as connexion:
        statistiques = traiter_documents(connexion, Path(arguments.racine))
    print(
        f"{statistiques['documents']} documents chunkés ({statistiques['chunks']} chunks), "
        f"{statistiques['inchanges']} inchangés (reprise sur hash), "
        f"{statistiques['echecs']} échecs"
    )
    return 1 if statistiques["echecs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
