"""Machine à états du workflow de rédaction — prompt 3, étapes 0→5 (E3.1).

Fonctions PURES (aucune DB, aucun LLM) : transitions d'étapes et règles du
registre des hypothèses. Les invariants produit qu'elles portent :

- règle 5 du prompt : on n'avance qu'après un « Oui » explicite du PO ; un
  « Non » laisse l'étape inchangée (itération) ;
- règle 1 : l'interview pose au maximum 3 questions par message ;
- règle 3 + arbitrage A8 : **une validation d'étape ne lève JAMAIS une
  hypothèse** — chaque [HYPOTHÈSE À VALIDER] est confirmée ou rejetée
  individuellement ; les non levées suivent la session jusqu'à la synthèse
  (récapitulatif transmis à l'export E5).

Le branchement Albert + RAG (/contexte) sur chaque étape arrive en E3.2.
"""

import re
from dataclasses import dataclass

from sia_api.gabarit import MARQUEUR_HYPOTHESE

ETAPES = (
    "recuperation_feature",  # étape 0
    "interview",  # étape 1
    "stories_candidates",  # étape 2
    "redaction",  # étape 3
    "controle_dor",  # étape 4
    "synthese",  # étape 5
)

QUESTIONS_MAX_PAR_LOT = 3  # règle 1 du prompt 3

ORIGINES = ("corpus", "po", "modele")  # marquage A3 : corpus cité / déclaré PO / modèle


def avancer(etape: str, valide: bool) -> str:
    """Transition d'étape (règle 5) : « Oui » avance, « Non » itère sur place."""
    if etape not in ETAPES:
        raise ValueError(f"étape inconnue : {etape}")
    if not valide:
        return etape
    index = ETAPES.index(etape)
    return ETAPES[min(index + 1, len(ETAPES) - 1)]


def est_terminale(etape: str) -> bool:
    return etape == ETAPES[-1]


# Phrases de CONSIGNE citant le marqueur comme convention, pas comme hypothèse
# (« je marquerai les incertitudes comme [HYPOTHÈSE À VALIDER] ») — bruit du
# registre constaté en session de validation (06/07/2026). Heuristique assumée :
# liste courte de tournures méta, en minuscules.
_TOURNURES_CONSIGNE = (
    "marquerai",
    "noterai",
    "seront considéré",
    "sera considéré",
    "porte la mention",
    "portent la mention",
    "je propose la question",
)


def _est_consigne(ligne: str) -> bool:
    minuscule = ligne.lower()
    return any(tournure in minuscule for tournure in _TOURNURES_CONSIGNE)


def extraire_hypotheses(texte: str) -> list[str]:
    """Lignes porteuses du marqueur — chaque entrée alimente le registre (A8).

    Les phrases de consigne (le marqueur cité comme convention) sont écartées :
    elles ne sont pas des hypothèses à lever. Les entêtes markdown non plus
    (« ### Hypothèses encore en attente ([HYPOTHÈSE À VALIDER]) » — titre de
    section entré au registre, constaté session 11, 06/07/2026).
    """
    return [
        ligne.strip()
        for ligne in texte.splitlines()
        if MARQUEUR_HYPOTHESE in ligne
        and not _est_consigne(ligne)
        and not ligne.lstrip().startswith("#")
    ]


# Décoration markdown à neutraliser pour comparer deux formulations d'une même
# hypothèse (puce, ligne de tableau, gras, italique…).
_DECORATION_MARKDOWN = str.maketrans("", "", "|*_`>#")


def cle_hypothese(texte: str) -> str:
    """Clé de déduplication du registre (A8) — la MÊME hypothèse reformulée avec
    une décoration différente (puce vs ligne de tableau vs récapitulatif) ne doit
    pas créer une nouvelle entrée (bruit constaté session de validation)."""
    texte = texte.translate(_DECORATION_MARKDOWN)
    texte = re.sub(r"\s+", " ", texte).strip(" -").rstrip(" .")
    return texte.lower()


def _tokens_hypothese(texte: str) -> frozenset[str]:
    """Termes porteurs de sens d'une hypothèse (mots > 3 lettres + nombres)."""
    return frozenset(
        mot for mot in re.findall(r"[\w']+", cle_hypothese(texte)) if len(mot) > 3 or mot.isdigit()
    )


# Sous ce seuil, deux formulations sont considérées distinctes : la dédup ne
# doit JAMAIS avaler une hypothèse réellement nouvelle (ce serait une perte —
# contraire à A8). 0,8 calibré sur les paires réelles de la session 11.
SEUIL_RECOUVREMENT_DOUBLON = 0.8


def est_doublon_hypothese(texte: str, existants: list[str]) -> bool:
    """La MÊME hypothèse RE-FORMULÉE ne rentre pas deux fois au registre (A8).

    Bruit constaté session 11 (06/07/2026, 18 « en attente ») : les
    récapitulatifs du modèle re-listent les hypothèses déjà enregistrées sous
    d'autres mots (« - #3 : Taille maximale de la pièce jointe = 10 Mo, comme
    indiqué dans les CA » vs « Taille maximale d'une pièce jointe : 10 Mo ») —
    la clé normalisée ne les rapproche pas. Doublon si les termes porteurs de
    sens de la formulation la plus courte sont recouverts à ≥ 80 % par l'autre.
    C'est une dédup de la même hypothèse, jamais une levée.
    """
    tokens = _tokens_hypothese(texte)
    if not tokens:
        return False
    for existant in existants:
        tokens_existant = _tokens_hypothese(existant)
        if not tokens_existant:
            continue
        petit, grand = sorted((tokens, tokens_existant), key=len)
        if len(petit & grand) / len(petit) >= SEUIL_RECOUVREMENT_DOUBLON:
            return True
    return False


# Rapprochement décision d'interview ↔ registre (A8, S2.13) : le moteur émet ce
# marqueur quand un message du PO (ou un extrait cité) tranche une hypothèse déjà
# au registre. Ce n'est qu'une PROPOSITION : la levée reste la décision
# individuelle du PO — le statut de l'hypothèse n'est jamais modifié ici.
MARQUEUR_LEVEE_PROPOSEE = "[LEVÉE PROPOSÉE"

_MOTIF_LEVEE_PROPOSEE = re.compile(
    r"\[LEVÉE PROPOSÉE\s*:\s*#?(\d+)\s*[—–-]+\s*(confirmée|rejetée|confirmee|rejetee)"
    r"\s*(?:[—–-]+\s*([^\]]*))?\]",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LeveeProposee:
    hypothese_id: int
    statut_propose: str  # "confirmee" | "rejetee"
    justification: str


def extraire_levees_proposees(texte: str, ids_en_attente: set[int]) -> list[LeveeProposee]:
    """Levées proposées par le moteur — filtrées sur le registre réellement en attente.

    Un identifiant inconnu ou déjà décidé est ignoré (le modèle peut se tromper
    de numéro) ; une ligne malformée est ignorée ; un même identifiant proposé
    deux fois ne compte qu'une fois (la première proposition gagne).
    """
    levees: list[LeveeProposee] = []
    vus: set[int] = set()
    for correspondance in _MOTIF_LEVEE_PROPOSEE.finditer(texte):
        hypothese_id = int(correspondance.group(1))
        if hypothese_id not in ids_en_attente or hypothese_id in vus:
            continue
        statut = "confirmee" if correspondance.group(2).lower().startswith("confirm") else "rejetee"
        vus.add(hypothese_id)
        levees.append(
            LeveeProposee(
                hypothese_id=hypothese_id,
                statut_propose=statut,
                justification=(correspondance.group(3) or "").strip(),
            )
        )
    return levees


def compter_questions(texte: str) -> int:
    """Nombre de questions d'un message d'interview (contrôle de la règle 1)."""
    return texte.count("?")


def verifier_lot_interview(texte: str) -> list[str]:
    """Violations de la règle 1 pour un message d'interview du moteur."""
    nb_questions = compter_questions(texte)
    if nb_questions > QUESTIONS_MAX_PAR_LOT:
        return [
            f"{nb_questions} questions dans le lot — le prompt 3 en autorise "
            f"{QUESTIONS_MAX_PAR_LOT} au maximum par message (règle 1)"
        ]
    return []
