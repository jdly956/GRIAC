"""Gabarit interne des User Stories — templates structurés & validateur (S1.10).

Source unique : `api/prompts/prompt-3-rediger-mes-user-stories.md` (étape 3 pour
le format US, étape 4 pour le tableau DoR). Ce module extrait le gabarit en
constantes structurées et fournit le contrôle de conformité qu'utiliseront le
moteur de rédaction (E3, contrôle DoR automatisé) et le harnais d'évals (E6).

Les marqueurs [HYPOTHÈSE À VALIDER] ne sont JAMAIS bloquants : ils sont relevés
et restitués (registre des hypothèses, arbitrage A8 — jamais levés silencieusement).

CLI : `python -m sia_api.gabarit <fichier.md>` valide toutes les stories d'un
fichier (séparées par `---`) et affiche un rapport par story.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

MARQUEUR_HYPOTHESE = "[HYPOTHÈSE À VALIDER]"

# Blocs dont le contenu est attendu sur la même ligne que le marqueur gras.
BLOCS_RECIT = ("En tant que", "Je veux", "Afin de")
BLOCS_CHAMPS = (
    "Contexte",
    "Écran / module",
    "Parcours concerné",
    "Pré-requis",
    "Règle(s) métier",
    "Maquettes",
)

COLONNES_TABLEAU_CA = ("#", "Étant donné que…", "Lorsque…", "Alors…")

# Étape 2 du prompt 3 — vue synthétique des stories candidates (consommée par E3).
COLONNES_STORIES_CANDIDATES = (
    "#",
    "Titre",
    "En tant que… je veux… afin de… (1 ligne)",
    "Type (fonctionnelle / enabler)",
    "Couvre quel(s) CA de la Feature",
    "Dépend de",
    "Ordre suggéré",
)

# Étape 4 du prompt 3 — tableau DoR : libellés exacts, dans l'ordre.
CRITERES_DOR = (
    "Le besoin (le pourquoi) est compréhensible",
    "Rôle et parcours utilisateur explicites",
    "Un use case concret est précisé",
    "Les prérequis / règles métier sont indiqués",
    "Les dépendances sont identifiées (API, équipes, données, ops…)",
    "L'US est estimée et revue en backlog refinement",
    "Des critères d'acceptation existent",
    "Jeux de données et environnement de test identifiés",
    "L'US est testable par le PO / démontrable en sprint review",
    "Composants DSFR utilisés, information structurée, libellés explicites, utilisable au clavier",
)
STATUTS_DOR = ("✅", "⚠️", "❌", "🔵")
CRITERE_DOR_REFINEMENT = "L'US est estimée et revue en backlog refinement"

# Adverbes flous proscrits par la règle 4 du prompt (avertissement, non bloquant :
# le PO reste l'arbitre final de sa formulation).
ADVERBES_FLOUS = ("rapidement", "facilement", "intuitif", "intuitive", "simplement", "convivial")


@dataclass
class RapportConformite:
    violations: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    nb_ca: int = 0

    @property
    def conforme(self) -> bool:
        return not self.violations


def extraire_stories_us(texte: str) -> list[str]:
    """Découpe un fichier markdown en stories US (séparateur `---`)."""
    segments = re.split(r"\n-{3,}\n", texte)
    return [segment.strip() for segment in segments if "**US — " in segment]


def _cellules(ligne: str) -> list[str]:
    return [cellule.strip() for cellule in ligne.strip().strip("|").split("|")]


def _normaliser(texte: str) -> str:
    return texte.replace("...", "…").strip().lower()


# Typographie réelle des sorties Albert (constatée pod 06/07/2026, faux positifs
# du contrôle S2.12) : tirets insécables et apostrophes typographiques là où le
# gabarit attend l'ASCII. Les tirets cadratins (—) sont préservés : l'entête
# « **US — Titre** » en dépend.
_CANONICALISATION = str.maketrans(
    {
        "‐": "-",  # trait d'union
        "‑": "-",  # trait d'union insécable (« Pré‑requis »)
        "’": "'",  # apostrophe typographique (« d'acceptation »)
        " ": " ",  # espace insécable
        " ": " ",  # espace fine insécable
    }
)


def _canonicaliser(texte: str) -> str:
    return texte.translate(_CANONICALISATION)


def _section(texte: str, entete: str) -> str | None:
    """Contenu entre `**entete**` et le prochain bloc gras en début de ligne."""
    motif = re.compile(
        rf"^\*\*{re.escape(entete)}\*\*.*?$(.*?)(?=^\*\*|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    correspondance = motif.search(texte)
    return correspondance.group(1) if correspondance else None


def _lignes_tableau(section: str) -> list[list[str]]:
    lignes = [ligne for ligne in section.splitlines() if ligne.strip().startswith("|")]
    return [_cellules(ligne) for ligne in lignes]


def valider_us(texte: str) -> RapportConformite:
    """Contrôle de conformité d'UNE story au format interne (prompt 3, étape 3)."""
    texte = _canonicaliser(texte)
    rapport = RapportConformite()

    if not re.search(r"\*\*US — .+?\*\*", texte):
        rapport.violations.append("entête manquante : « **US — {Titre}** »")

    # [ \t]* et non \s* : \s avalerait le saut de ligne et capturerait la ligne suivante.
    for bloc in BLOCS_RECIT:
        correspondance = re.search(rf"^\*\*{re.escape(bloc)}\*\*[ \t]*(.*)$", texte, re.MULTILINE)
        if not correspondance:
            rapport.violations.append(f"bloc manquant : « **{bloc}** »")
        elif not correspondance.group(1).strip():
            rapport.violations.append(f"bloc vide : « **{bloc}** »")

    for bloc in BLOCS_CHAMPS:
        correspondance = re.search(
            rf"^\*\*{re.escape(bloc)}\*\*[ \t]*:?[ \t]*(.*)$", texte, re.MULTILINE
        )
        if not correspondance:
            rapport.violations.append(f"bloc manquant : « **{bloc}** »")
        elif not correspondance.group(1).strip():
            # Le contenu peut suivre sur les lignes d'après (listes, numérotations —
            # forme réelle des sorties Albert) : vide seulement si la section l'est.
            section = _section(texte, bloc)
            if not (section and section.strip()):
                rapport.violations.append(f"bloc vide : « **{bloc}** »")

    section_attendu = _section(texte, "Attendu fonctionnel")
    if section_attendu is None:
        rapport.violations.append("bloc manquant : « **Attendu fonctionnel** »")
    elif not re.search(r"^\s*- .+", section_attendu, re.MULTILINE):
        # Le contenu peut aussi tenir sur la ligne du bloc (forme courte du gabarit).
        ligne = re.search(r"^\*\*Attendu fonctionnel\*\*[ \t]*:?[ \t]*(.+)$", texte, re.MULTILINE)
        if not (ligne and ligne.group(1).strip()):
            rapport.violations.append("« Attendu fonctionnel » sans aucun attendu listé")

    section_ca = _section(texte, "Critères d'acceptation")
    if section_ca is None:
        rapport.violations.append("bloc manquant : « **Critères d'acceptation** »")
    else:
        lignes = _lignes_tableau(section_ca)
        if not lignes:
            rapport.violations.append("tableau des critères d'acceptation absent")
        else:
            entete_attendue = [_normaliser(colonne) for colonne in COLONNES_TABLEAU_CA]
            if [_normaliser(cellule) for cellule in lignes[0]] != entete_attendue:
                rapport.violations.append(
                    "colonnes du tableau des CA non conformes (attendu : "
                    f"{' | '.join(COLONNES_TABLEAU_CA)})"
                )
            donnees = [
                cellules
                for cellules in lignes[1:]
                if not all(re.fullmatch(r":?-{3,}:?", cellule) for cellule in cellules)
            ]
            if not donnees:
                rapport.violations.append("tableau des CA sans aucune ligne de critère")
            for cellules in donnees:
                if len(cellules) != len(COLONNES_TABLEAU_CA) or any(
                    not cellule for cellule in cellules
                ):
                    rapport.violations.append(
                        f"ligne de CA incomplète : « {' | '.join(cellules)} »"
                    )
            rapport.nb_ca = len(donnees)

    section_dsfr = _section(texte, "Critères d'accessibilité")
    if section_dsfr is None:
        rapport.violations.append("bloc manquant : « **Critères d'accessibilité** » (DSFR)")
    elif not re.search(r"^\s*- .+", section_dsfr, re.MULTILINE):
        rapport.violations.append("« Critères d'accessibilité » sans aucun critère listé")

    for adverbe in ADVERBES_FLOUS:
        if re.search(rf"\b{adverbe}\b", texte, re.IGNORECASE):
            rapport.avertissements.append(
                f"formulation floue « {adverbe} » (règle 4 du gabarit : formulations vérifiables)"
            )

    for ligne in texte.splitlines():
        if MARQUEUR_HYPOTHESE in ligne:
            rapport.hypotheses.append(ligne.strip())

    return rapport


def valider_dor(texte: str) -> RapportConformite:
    """Contrôle du tableau DoR (prompt 3, étape 4) : 10 critères, statuts, justifications."""
    texte = _canonicaliser(texte)
    rapport = RapportConformite()
    lignes = _lignes_tableau(texte)
    if not lignes or [_normaliser(cellule) for cellule in lignes[0]] != [
        _normaliser(colonne) for colonne in ("Critère DoR", "Statut", "Justification")
    ]:
        rapport.violations.append(
            "tableau DoR absent ou colonnes non conformes (attendu : "
            "Critère DoR | Statut | Justification)"
        )
        return rapport

    donnees = [
        cellules
        for cellules in lignes[1:]
        if not all(re.fullmatch(r":?-{3,}:?", cellule) for cellule in cellules)
    ]
    criteres_vus = [cellules[0] for cellules in donnees if cellules]
    for critere in CRITERES_DOR:
        if critere not in criteres_vus:
            rapport.violations.append(f"critère DoR manquant : « {critere} »")

    for cellules in donnees:
        if len(cellules) != 3:
            rapport.violations.append(f"ligne DoR incomplète : « {' | '.join(cellules)} »")
            continue
        critere, statut, justification = cellules
        if not any(symbole in statut for symbole in STATUTS_DOR):
            rapport.violations.append(
                f"statut DoR invalide pour « {critere} » (attendu : {' '.join(STATUTS_DOR)})"
            )
        if not justification:
            rapport.violations.append(f"justification manquante pour « {critere} »")
        if critere == CRITERE_DOR_REFINEMENT and "🔵" not in statut:
            rapport.violations.append(
                "« estimée et revue en backlog refinement » doit rester 🔵 : "
                "l'estimation relève de l'équipe, jamais de l'IA"
            )
        if MARQUEUR_HYPOTHESE in justification:
            rapport.hypotheses.append(f"{critere} : {justification}")

    return rapport


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 1:
        print("Usage : python -m sia_api.gabarit <fichier.md>", file=sys.stderr)
        return 2
    texte = Path(arguments[0]).read_text(encoding="utf-8")
    stories = extraire_stories_us(texte)
    if not stories:
        print("Aucune story « **US — … » trouvée dans le fichier.", file=sys.stderr)
        return 2
    code_retour = 0
    for story in stories:
        titre = re.search(r"\*\*US — (.+?)\*\*", story)
        rapport = valider_us(story)
        verdict = "CONFORME" if rapport.conforme else "NON CONFORME"
        print(
            f"[{verdict}] {titre.group(1) if titre else '(sans titre)'} — "
            f"{rapport.nb_ca} CA, {len(rapport.hypotheses)} hypothèse(s) à valider, "
            f"{len(rapport.avertissements)} avertissement(s)"
        )
        for violation in rapport.violations:
            print(f"    violation : {violation}")
        for avertissement in rapport.avertissements:
            print(f"    avertissement : {avertissement}")
        code_retour = code_retour or (0 if rapport.conforme else 1)
    return code_retour


if __name__ == "__main__":
    raise SystemExit(main())
