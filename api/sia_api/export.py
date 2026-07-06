"""Export des stories d'une session — CSV Jira + copier-coller formaté (E5, S2.7).

Jira n'est pas joignable depuis l'environnement (D10) : l'export est un CSV
importable + un markdown à copier-coller, pas un appel API. Arbitrage A8 :
**l'export est autorisé même avec des hypothèses non levées**, mais il est
accompagné d'un avertissement et du récapitulatif — jamais silencieux.

v0 assumée : les stories sont extraites des messages de l'assistant aux étapes
rédaction/contrôle DoR/synthèse (le format du prompt 3 encadre chaque US de
`---`). En cas d'itérations (règle 5), la DERNIÈRE version d'un même titre
gagne. La conformité au gabarit est évaluée par le validateur S1.10 et
annotée dans l'export markdown.
"""

import csv
import io
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from sia_api.db import get_connexion
from sia_api.gabarit import extraire_stories_us, titre_us, valider_us

router = APIRouter(tags=["export"])

Connexion = Annotated[Any, Depends(get_connexion)]

ETAPES_AVEC_STORIES = ("redaction", "controle_dor", "synthese")


def _titre(story: str) -> str:
    return titre_us(story) or "(sans titre)"


def extraire_stories_session(messages: list[tuple[str, str, str]]) -> list[str]:
    """Stories des messages assistant (étapes de rédaction et suivantes).

    Dédupliquées par titre, la dernière version gagne (itérations règle 5).
    """
    par_titre: dict[str, str] = {}
    for role, etape, contenu in messages:
        if role != "assistant" or etape not in ETAPES_AVEC_STORIES:
            continue
        for story in extraire_stories_us(contenu):
            par_titre[_titre(story)] = story
    return list(par_titre.values())


def generer_csv_jira(stories: list[str]) -> str:
    """CSV importable Jira : Summary / Issue Type / Description (markdown intégral)."""
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    ecrivain.writerow(["Summary", "Issue Type", "Description"])
    for story in stories:
        ecrivain.writerow([_titre(story), "Story", story])
    return tampon.getvalue()


def generer_markdown(stories: list[str], hypotheses_en_attente: list[str]) -> str:
    """Copier-coller formaté : avertissement + récapitulatif A8 en tête, puis les US."""
    blocs = ["# Export des user stories — SIA PO", ""]
    if hypotheses_en_attente:
        blocs += [
            f"> ⚠️ **{len(hypotheses_en_attente)} hypothèse(s) non levée(s)** — export autorisé "
            "mais ce récapitulatif doit accompagner les stories (arbitrage A8) :",
            "",
        ]
        blocs += [f"> - {texte}" for texte in hypotheses_en_attente]
        blocs.append("")
    for story in stories:
        rapport = valider_us(story)
        conformite = (
            "conforme au gabarit interne"
            if rapport.conforme
            else "NON CONFORME au gabarit : " + " ; ".join(rapport.violations)
        )
        blocs += ["---", f"<!-- Contrôle S1.10 : {conformite} -->", "", story, ""]
    return "\n".join(blocs)


def _charger_session(curseur, session_id: int) -> tuple[list[str], list[str]]:
    curseur.execute("SELECT id FROM workflow_sessions WHERE id = %(id)s", {"id": session_id})
    if curseur.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
    curseur.execute(
        "SELECT role, etape, contenu FROM workflow_messages WHERE session_id = %(id)s ORDER BY id",
        {"id": session_id},
    )
    stories = extraire_stories_session([(m[0], m[1], m[2]) for m in curseur.fetchall()])
    if not stories:
        raise HTTPException(
            status_code=409,
            detail="Aucune story rédigée à exporter — la session doit avoir produit des US "
            "au format interne (étape rédaction).",
        )
    curseur.execute(
        "SELECT texte FROM workflow_hypotheses "
        "WHERE session_id = %(id)s AND statut = 'en_attente' ORDER BY id",
        {"id": session_id},
    )
    hypotheses = [ligne[0] for ligne in curseur.fetchall()]
    return stories, hypotheses


@router.get("/workflows/{session_id}/export/jira.csv")
def export_csv(session_id: int, connexion: Connexion) -> PlainTextResponse:
    """CSV Jira. L'avertissement A8 voyage dans l'en-tête X-Hypotheses-Non-Levees
    et dans l'export markdown joint — le CSV reste importable tel quel."""
    with connexion.cursor() as curseur:
        stories, hypotheses = _charger_session(curseur, session_id)
    return PlainTextResponse(
        generer_csv_jira(stories),
        media_type="text/csv; charset=utf-8",
        headers={"X-Hypotheses-Non-Levees": str(len(hypotheses))},
    )


@router.get("/workflows/{session_id}/export/markdown")
def export_markdown(session_id: int, connexion: Connexion) -> PlainTextResponse:
    """Copier-coller formaté, récapitulatif A8 inclus."""
    with connexion.cursor() as curseur:
        stories, hypotheses = _charger_session(curseur, session_id)
    return PlainTextResponse(
        generer_markdown(stories, hypotheses), media_type="text/markdown; charset=utf-8"
    )
