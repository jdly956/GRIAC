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


def extraire_hypotheses(texte: str) -> list[str]:
    """Lignes porteuses du marqueur — chaque entrée alimente le registre (A8)."""
    return [ligne.strip() for ligne in texte.splitlines() if MARQUEUR_HYPOTHESE in ligne]


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
