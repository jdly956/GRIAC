"""Harnais d'évals E6 : benchmark de génération sur la grille 3 axes.

`make eval` compare les modèles de chat Albert (par défaut `openweight-large`
vs `openweight-medium`) sur les stories de référence : gold (`/evals/gold/`)
dès fourniture, repli silver sinon — un score obtenu sur silver ne vaut pas
étalonnage (candidates non validées, le rapport l'affiche).

Chaque cas : un brief est reconstitué depuis la story de référence (récit,
pré-requis, règles métier, attendus) ; le modèle génère l'US complète ; la
sortie est scorée automatiquement sur la grille (proxys v0 — la grille
manuelle PO de `evals/grille-notation.md` reste la référence) :
- gabarit : conformité S1.10 (`valider_us`), -0,2 par violation ;
- exactitude : les règles métier du brief se retrouvent dans la story et
  aucun nombre étranger au brief n'apparaît hors ligne [HYPOTHÈSE À VALIDER]
  (anti-invention ; « 200 » exempté — zoom texte RGAA standard) ;
- complétude : blocs du gabarit remplis + ratio de CA vs la référence.

Relevés informels par appel (latence, tokens) : préparation du test de débit
sous quotas (tpd 2,46 M — S1.5). Aucun appel réseau dans les TU : le client
est injecté.
"""

import argparse
import re
import time
from dataclasses import dataclass
from pathlib import Path

from sia_api.albert import creer_client
from sia_api.config import charger_settings
from sia_api.gabarit import (
    BLOCS_CHAMPS,
    BLOCS_RECIT,
    MARQUEUR_HYPOTHESE,
    extraire_stories_us,
    titre_us,
    valider_us,
)

DOSSIER_GOLD = Path(__file__).parents[2] / "evals" / "gold"
FICHIER_SILVER = Path(__file__).parents[2] / "evals" / "silver" / "stories-silver-candidates.md"

MODELES_DEFAUT = "openweight-large,openweight-medium"
MAX_TOKENS_REPONSE = 4096  # modèle à raisonnement : ne jamais brider trop bas (S1.5)
NOMBRES_EXEMPTES = {"200"}  # zoom texte 200 % : critère RGAA standard, pas une invention

CHAMPS_BRIEF = (
    "**En tant que**",
    "**Je veux**",
    "**Afin de**",
    "**Pré-requis**",
    "**Règle(s) métier**",
)

PROMPT_SYSTEME_EVAL = (
    "Tu rédiges une user story SAFe pour un téléservice de l'administration française, "
    "au format EXACT du gabarit interne : titre '**US — …**', blocs '**En tant que**', "
    "'**Je veux**', '**Afin de**', puis les champs '**Contexte**', '**Écran / module**', "
    "'**Parcours concerné**', '**Pré-requis**', '**Règle(s) métier**', "
    "'**Attendu fonctionnel**', '**Maquettes**', le tableau '**Critères d'acceptation**' "
    "(colonnes | # | Étant donné que… | Lorsque… | Alors… |) et enfin "
    "'**Critères d'accessibilité**' (DSFR/RGAA). "
    f"Toute information absente du brief est marquée {MARQUEUR_HYPOTHESE} — n'invente rien. "
    "Réponds uniquement avec la story, sans préambule."
)


@dataclass
class Cas:
    titre: str
    brief: str
    reference: str


@dataclass
class Scores:
    gabarit: float
    exactitude: float
    completude: float

    @property
    def moyenne(self) -> float:
        return round((self.gabarit + self.exactitude + self.completude) / 3, 3)


@dataclass
class Resultat:
    modele: str
    cas: str
    scores: Scores
    duree_s: float
    tokens_sortie: int | None
    erreur: str | None = None


def _titre(story: str) -> str:
    return titre_us(story) or "(sans titre)"


def charger_cas() -> tuple[list[Cas], str]:
    """Cas de benchmark : gold prioritaire, repli silver (même logique que le few-shot S2.6)."""
    sources: list[tuple[str, list[str]]] = []
    if DOSSIER_GOLD.is_dir():
        sources.append(
            ("gold", [f.read_text(encoding="utf-8") for f in sorted(DOSSIER_GOLD.glob("*.md"))])
        )
    if FICHIER_SILVER.is_file():
        sources.append(("silver", [FICHIER_SILVER.read_text(encoding="utf-8")]))
    for origine, textes in sources:
        stories = [story for texte in textes for story in extraire_stories_us(texte)]
        if stories:
            cas = [Cas(titre=_titre(s), brief=construire_brief(s), reference=s) for s in stories]
            return cas, origine
    return [], "aucune"


def construire_brief(story: str) -> str:
    """Reconstitue l'entrée PO : récit, pré-requis, règles métier, attendus fonctionnels.

    Le reste (CA, accessibilité, contexte rédigé) reste dans la référence : c'est
    précisément ce que le modèle doit produire.
    """
    brief: list[str] = []
    dans_attendus = False
    for ligne in story.splitlines():
        nette = ligne.strip()
        if nette.startswith("**Attendu fonctionnel**"):
            dans_attendus = True
            brief.append(nette)
            continue
        if dans_attendus:
            if nette.startswith("- "):
                brief.append(nette)
                continue
            if nette:
                dans_attendus = False
        if any(nette.startswith(champ) for champ in CHAMPS_BRIEF):
            brief.append(nette)
    return "\n".join(brief)


# --- grille 3 axes (proxys v0 automatiques) ---


def score_gabarit(genere: str) -> float:
    """Conformité au gabarit interne — source unique : le validateur S1.10."""
    rapport = valider_us(genere)
    return round(max(0.0, 1.0 - 0.2 * len(rapport.violations)), 3)


def _tokens_significatifs(texte: str) -> set[str]:
    return {mot for mot in re.findall(r"[\w’']+", texte.lower()) if len(mot) > 3}


def score_exactitude(genere: str, brief: str) -> float:
    """Les règles métier du brief se retrouvent ; pas de nombre inventé non marqué."""
    ligne_regles = next(
        (ligne for ligne in brief.splitlines() if ligne.startswith("**Règle(s) métier**")), ""
    )
    regles = [r.strip() for r in ligne_regles.split(":", 1)[-1].split(";") if r.strip()]
    mots_generes = _tokens_significatifs(genere)
    if regles:
        couvertes = 0
        for regle in regles:
            mots_regle = _tokens_significatifs(regle)
            if not mots_regle:
                continue
            if len(mots_regle & mots_generes) / len(mots_regle) >= 0.6:
                couvertes += 1
        base = couvertes / len(regles)
    else:
        base = 1.0
    nombres_brief = set(re.findall(r"\d+", brief))
    inventions = 0
    for ligne in genere.splitlines():
        if MARQUEUR_HYPOTHESE in ligne:
            continue
        for nombre in re.findall(r"\d{2,}", ligne):
            if nombre not in nombres_brief and nombre not in NOMBRES_EXEMPTES:
                inventions += 1
    return round(max(0.0, min(1.0, base - 0.1 * min(inventions, 5))), 3)


def _nb_lignes_ca(texte: str) -> int:
    return len(re.findall(r"^\|\s*CA\d", texte, flags=re.MULTILINE))


def score_completude(genere: str, reference: str) -> float:
    """Blocs du gabarit remplis + autant de CA que la référence (ratio capé à 1)."""
    blocs_attendus = [f"**{bloc}**" for bloc in (*BLOCS_RECIT, *BLOCS_CHAMPS)] + [
        "**Critères d'acceptation**",
        "**Critères d'accessibilité**",
    ]
    presents = sum(1 for bloc in blocs_attendus if bloc in genere)
    ratio_blocs = presents / len(blocs_attendus)
    ratio_ca = min(1.0, _nb_lignes_ca(genere) / max(1, _nb_lignes_ca(reference)))
    return round(0.5 * ratio_blocs + 0.5 * ratio_ca, 3)


def evaluer(genere: str, cas: Cas) -> Scores:
    return Scores(
        gabarit=score_gabarit(genere),
        exactitude=score_exactitude(genere, cas.brief),
        completude=score_completude(genere, cas.reference),
    )


# --- exécution du benchmark ---


def generer_story(client, modele: str, brief: str) -> tuple[str, int | None]:
    reponse = client.chat.completions.create(
        model=modele,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEME_EVAL},
            {"role": "user", "content": f"Brief de la story :\n\n{brief}"},
        ],
        max_tokens=MAX_TOKENS_REPONSE,
    )
    contenu = reponse.choices[0].message.content or ""
    usage = getattr(reponse, "usage", None)
    return contenu, getattr(usage, "completion_tokens", None)


def executer(
    client, modeles: list[str], cas: list[Cas], horloge=time.perf_counter
) -> list[Resultat]:
    resultats: list[Resultat] = []
    for modele in modeles:
        for un_cas in cas:
            debut = horloge()
            erreur: str | None = None
            contenu, tokens = "", None
            try:
                contenu, tokens = generer_story(client, modele, un_cas.brief)
            except Exception as exception:  # un modèle en échec n'arrête pas le banc
                erreur = f"{type(exception).__name__}: {str(exception)[:200]}"
            duree = round(horloge() - debut, 2)
            if not contenu.strip():
                erreur = erreur or "réponse vide (gotcha raisonnement S1.5 ?)"
                scores = Scores(0.0, 0.0, 0.0)
            else:
                scores = evaluer(contenu, un_cas)
            resultats.append(
                Resultat(
                    modele=modele,
                    cas=un_cas.titre,
                    scores=scores,
                    duree_s=duree,
                    tokens_sortie=tokens,
                    erreur=erreur,
                )
            )
    return resultats


def generer_rapport(resultats: list[Resultat], origine: str) -> str:
    lignes = ["# Benchmark génération — grille 3 axes (E6)", ""]
    if origine == "silver":
        lignes += [
            "> ⚠️ Références **SILVER** (candidates non validées) : scores indicatifs, "
            "à recalibrer sur `/evals/gold/` dès fourniture.",
            "",
        ]
    lignes += [
        "| Modèle | Cas | Gabarit | Exactitude | Complétude | Moyenne "
        "| Durée (s) | Tokens | Erreur |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resultats:
        lignes.append(
            f"| {r.modele} | {r.cas} | {r.scores.gabarit} | {r.scores.exactitude} "
            f"| {r.scores.completude} | {r.scores.moyenne} | {r.duree_s} "
            f"| {r.tokens_sortie if r.tokens_sortie is not None else '—'} | {r.erreur or '—'} |"
        )
    lignes.append("")
    modeles = sorted({r.modele for r in resultats})
    lignes.append("## Moyennes par modèle")
    lignes.append("")
    for modele in modeles:
        siens = [r for r in resultats if r.modele == modele]
        moyenne = round(sum(r.scores.moyenne for r in siens) / len(siens), 3)
        echecs = sum(1 for r in siens if r.erreur)
        lignes.append(f"- **{modele}** : {moyenne} ({len(siens)} cas, {echecs} échec(s))")
    lignes.append("")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description="Benchmark génération E6 (grille 3 axes)")
    analyseur.add_argument("--modeles", default=MODELES_DEFAUT, help="alias Albert, séparés par ,")
    analyseur.add_argument("--max-cas", type=int, default=None, help="limite le nombre de cas")
    analyseur.add_argument("--sortie", default=None, help="chemin du rapport markdown")
    options = analyseur.parse_args(argv)

    cas, origine = charger_cas()
    if not cas:
        print("Aucune story de référence dans evals/gold/ ni evals/silver/ — rien à évaluer.")
        return 1
    if options.max_cas:
        cas = cas[: options.max_cas]
    modeles = [m.strip() for m in options.modeles.split(",") if m.strip()]
    print(f"{len(cas)} cas ({origine}) × {len(modeles)} modèle(s) — appels Albert réels.")

    client = creer_client(charger_settings())
    resultats = executer(client, modeles, cas)
    rapport = generer_rapport(resultats, origine)
    print(rapport)
    if options.sortie:
        Path(options.sortie).write_text(rapport, encoding="utf-8")
        print(f"Rapport écrit : {options.sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
