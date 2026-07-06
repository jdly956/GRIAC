"""Stories d'une session : lecture du contenu + ÉDITION — S3.13 (lot pré-pilote).

L'édition était promise par la cible E4 (« affichage sources, édition,
note 1–5 ») et jamais livrée : le PO devait re-générer pour corriger deux
mots. La version éditée est stockée par titre (`story_editions`) et **gagne
à l'export** (E5) — le titre reste la clé, l'édition porte sur le contenu.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sia_api.db import get_connexion
from sia_api.export import extraire_stories_session
from sia_api.gabarit import titre_us

router = APIRouter(tags=["stories"])

Connexion = Annotated[Any, Depends(get_connexion)]


class StoryContenu(BaseModel):
    titre: str
    contenu: str
    editee: bool


class EditionEntree(BaseModel):
    titre: str = Field(min_length=1)
    contenu: str = Field(min_length=1)


def lire_editions(curseur, session_id: int) -> dict[str, str]:
    curseur.execute(
        "SELECT titre, contenu FROM story_editions WHERE session_id = %(id)s",
        {"id": session_id},
    )
    return {ligne[0]: ligne[1] for ligne in curseur.fetchall()}


@router.get("/workflows/{session_id}/stories/contenus")
def stories_contenus(session_id: int, connexion: Connexion) -> list[StoryContenu]:
    """Les stories de la session, version éditée prioritaire (S3.13)."""
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT role, etape, contenu FROM workflow_messages "
            "WHERE session_id = %(id)s ORDER BY id",
            {"id": session_id},
        )
        stories = extraire_stories_session([(m[0], m[1], m[2]) for m in curseur.fetchall()])
        editions = lire_editions(curseur, session_id)
    return [
        StoryContenu(
            titre=titre_us(story) or "(sans titre)",
            contenu=editions.get(titre_us(story) or "(sans titre)", story),
            editee=(titre_us(story) or "(sans titre)") in editions,
        )
        for story in stories
    ]


@router.put("/workflows/{session_id}/stories/edition")
def editer_story(session_id: int, entree: EditionEntree, connexion: Connexion) -> StoryContenu:
    """La version éditée gagne à l'export — le taux d'édition devient réel (E4.4)."""
    with connexion.cursor() as curseur:
        curseur.execute("SELECT id FROM workflow_sessions WHERE id = %(id)s", {"id": session_id})
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "INSERT INTO story_editions (session_id, titre, contenu) "
            "VALUES (%(id)s, %(titre)s, %(contenu)s) "
            "ON CONFLICT (session_id, titre) "
            "DO UPDATE SET contenu = EXCLUDED.contenu, modifie_le = now()",
            {"id": session_id, "titre": entree.titre, "contenu": entree.contenu},
        )
    connexion.commit()
    return StoryContenu(titre=entree.titre, contenu=entree.contenu, editee=True)
