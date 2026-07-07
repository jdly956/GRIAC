"""Paramètres d'instance — S3.12 : le modèle de chat changeable depuis l'UI.

Réglage GLOBAL de l'instance partagée (arbitrage du 06/07/2026 — cohérent
avec A7, sans comptes). Précédence effective dans le moteur : surcharge UI
(table `parametres`) > `settings.albert_model_chat` (env d'infra au
démarrage > défaut du code). « Revenir au défaut » supprime la surcharge.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from sia_api.db import get_connexion

# Défaut du code (S2.14) — utilisé quand les settings du lifespan ne sont pas
# disponibles (TU sans démarrage réel) ; en prod le défaut effectif vient de
# `settings.albert_model_chat` (env > code).
MODELE_CHAT_DEFAUT_CODE = "openweight-medium"

router = APIRouter(tags=["parametres"])

Connexion = Annotated[Any, Depends(get_connexion)]

CLE_MODELE_CHAT = "modele_chat"

# Alias servis par Albert au catalogue du 03/07/2026 (S1.5) — le champ libre
# de l'écran permet tout autre alias (rotation de catalogue, ALLiaNCE).
MODELES_PROPOSES = ("openweight-medium", "openweight-large")


def lire_surcharge_modele(curseur) -> str | None:
    """La surcharge UI du modèle de chat, ou None — consommée par le moteur."""
    curseur.execute("SELECT valeur FROM parametres WHERE cle = %(cle)s", {"cle": CLE_MODELE_CHAT})
    ligne = curseur.fetchone()
    return ligne[0] if ligne else None


class Parametres(BaseModel):
    modele_chat: str | None  # surcharge UI (None = défaut env/code actif)
    modele_actif: str  # ce qui écrira réellement la prochaine réponse
    modeles_proposes: list[str]


class ModeleEntree(BaseModel):
    modele: str = Field(min_length=1)


def _defaut(request: Request) -> str:
    settings = getattr(request.app.state, "settings", None)
    return settings.albert_model_chat if settings else MODELE_CHAT_DEFAUT_CODE


@router.get("/parametres")
def lire_parametres(request: Request, connexion: Connexion) -> Parametres:
    with connexion.cursor() as curseur:
        surcharge = lire_surcharge_modele(curseur)
    return Parametres(
        modele_chat=surcharge,
        modele_actif=surcharge or _defaut(request),
        modeles_proposes=list(MODELES_PROPOSES),
    )


@router.put("/parametres/modele-chat")
def changer_modele(entree: ModeleEntree, connexion: Connexion) -> Parametres:
    """Surcharge appliquée aux NOUVEAUX appels, sans relance de l'api."""
    with connexion.cursor() as curseur:
        curseur.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (%(cle)s, %(valeur)s) "
            "ON CONFLICT (cle) DO UPDATE SET valeur = EXCLUDED.valeur, modifie_le = now()",
            {"cle": CLE_MODELE_CHAT, "valeur": entree.modele.strip()},
        )
    connexion.commit()
    modele = entree.modele.strip()
    return Parametres(
        modele_chat=modele, modele_actif=modele, modeles_proposes=list(MODELES_PROPOSES)
    )


@router.delete("/parametres/modele-chat")
def revenir_au_defaut(request: Request, connexion: Connexion) -> Parametres:
    with connexion.cursor() as curseur:
        curseur.execute("DELETE FROM parametres WHERE cle = %(cle)s", {"cle": CLE_MODELE_CHAT})
    connexion.commit()
    return Parametres(
        modele_chat=None, modele_actif=_defaut(request), modeles_proposes=list(MODELES_PROPOSES)
    )
