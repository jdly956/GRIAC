"""Feedback par story et télémétrie d'usage (E4.4).

Note 1-5 + commentaire par story (CLAUDE.md E4) et indicateurs d'usage. Sans
comptes utilisateurs (A7) ni accès Jira (D10), les trois indicateurs sont des
proxys v0 assumés :
- actifs hebdo → sessions créées par semaine ;
- % stories conservées → part des stories notées >= 4 ;
- taux d'édition → part des validations « Non » (itérations règle 5),
  journalisées par `POST /workflows/{id}/avancer` depuis S2.10.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sia_api.db import get_connexion
from sia_api.export import _titre, extraire_stories_session

router = APIRouter(tags=["feedback"])

Connexion = Annotated[Any, Depends(get_connexion)]


class FeedbackEntree(BaseModel):
    story_titre: str = Field(min_length=1)
    note: int = Field(ge=1, le=5)
    commentaire: str = ""


class Feedback(FeedbackEntree):
    id: int
    session_id: int


class SemaineActive(BaseModel):
    semaine: str  # lundi de la semaine (date_trunc ISO)
    sessions: int


class Telemetrie(BaseModel):
    sessions_total: int
    actifs_hebdo: list[SemaineActive]  # proxy A7 : sessions créées par semaine
    stories_notees: int
    note_moyenne: float | None
    pourcentage_conservees: float | None  # proxy v0 : note >= 4
    validations_total: int
    taux_edition: float | None  # proxy v0 : part des « Non » (règle 5)


@router.post("/workflows/{session_id}/feedback", status_code=201)
def noter_story(session_id: int, entree: FeedbackEntree, connexion: Connexion) -> Feedback:
    with connexion.cursor() as curseur:
        curseur.execute("SELECT id FROM workflow_sessions WHERE id = %(id)s", {"id": session_id})
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "INSERT INTO story_feedbacks (session_id, story_titre, note, commentaire) "
            "VALUES (%(sid)s, %(titre)s, %(note)s, %(commentaire)s) RETURNING id",
            {
                "sid": session_id,
                "titre": entree.story_titre,
                "note": entree.note,
                "commentaire": entree.commentaire,
            },
        )
        feedback_id = curseur.fetchone()[0]
    connexion.commit()
    return Feedback(id=feedback_id, session_id=session_id, **entree.model_dump())


@router.get("/workflows/{session_id}/stories")
def titres_stories(session_id: int, connexion: Connexion) -> list[str]:
    """Titres des US produites par la session — alimente le panneau de notation E4.4.

    Liste vide tant que l'étape de rédaction n'a rien produit (pas de 409 :
    l'écran masque simplement le panneau).
    """
    with connexion.cursor() as curseur:
        curseur.execute("SELECT id FROM workflow_sessions WHERE id = %(id)s", {"id": session_id})
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "SELECT role, etape, contenu FROM workflow_messages "
            "WHERE session_id = %(id)s ORDER BY id",
            {"id": session_id},
        )
        stories = extraire_stories_session([(m[0], m[1], m[2]) for m in curseur.fetchall()])
    return [_titre(story) for story in stories]


@router.get("/telemetrie")
def telemetrie(connexion: Connexion) -> Telemetrie:
    with connexion.cursor() as curseur:
        curseur.execute("SELECT count(*) FROM workflow_sessions")
        sessions_total = curseur.fetchone()[0]
        curseur.execute(
            "SELECT to_char(date_trunc('week', cree_le), 'YYYY-MM-DD') AS semaine, count(*) "
            "FROM workflow_sessions GROUP BY 1 ORDER BY 1"
        )
        actifs = [
            SemaineActive(semaine=ligne[0], sessions=ligne[1]) for ligne in curseur.fetchall()
        ]
        curseur.execute(
            "SELECT count(*), avg(note), count(*) FILTER (WHERE note >= 4) FROM story_feedbacks"
        )
        stories_notees, note_moyenne, conservees = curseur.fetchone()
        curseur.execute(
            "SELECT count(*), count(*) FILTER (WHERE NOT valide) FROM workflow_validations"
        )
        validations_total, iterations = curseur.fetchone()
    return Telemetrie(
        sessions_total=sessions_total,
        actifs_hebdo=actifs,
        stories_notees=stories_notees,
        note_moyenne=round(float(note_moyenne), 2) if note_moyenne is not None else None,
        pourcentage_conservees=(round(conservees / stories_notees, 3) if stories_notees else None),
        validations_total=validations_total,
        taux_edition=round(iterations / validations_total, 3) if validations_total else None,
    )
