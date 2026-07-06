"""API des sessions de workflow — persistance de la machine à états (E3.1).

CRUD des sessions (étape courante, conversation, registre des hypothèses) sur
le modèle des routes projets (S1.11) : SQL brut, connexion injectée, testable
sans base réelle. Le moteur conversationnel (Albert + RAG à chaque étape,
arbitrages A2/A9) branchera ses réponses ici en E3.2.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sia_api.db import get_connexion
from sia_api.workflow import ETAPES, avancer, cle_hypothese, est_terminale, extraire_hypotheses

router = APIRouter(tags=["workflow"])

Connexion = Annotated[Any, Depends(get_connexion)]


class SessionEntree(BaseModel):
    feature: str = Field(min_length=1, description="Feature validée collée par le PO (étape 0)")
    projet_id: int | None = None


class Hypothese(BaseModel):
    id: int
    texte: str
    origine: Literal["corpus", "po", "modele"]
    statut: Literal["en_attente", "confirmee", "rejetee"]
    # Levée proposée par le moteur (rapprochement interview↔registre) : une
    # SUGGESTION affichée à côté des boutons — elle ne lève jamais rien (A8).
    statut_propose: Literal["confirmee", "rejetee"] | None = None
    justification_proposee: str | None = None


class EtatSession(BaseModel):
    id: int
    etape: str
    projet_id: int | None
    hypotheses: list[Hypothese]
    nb_en_attente: int


class ValidationEntree(BaseModel):
    valide: bool  # règle 5 : Oui / Non
    commentaire: str = ""


class HypotheseEntree(BaseModel):
    texte: str = Field(min_length=1)
    origine: Literal["corpus", "po", "modele"] = "modele"


class DecisionEntree(BaseModel):
    statut: Literal["confirmee", "rejetee"]  # décision INDIVIDUELLE (A8)


def _lire_session(curseur, session_id: int) -> EtatSession | None:
    curseur.execute(
        "SELECT id, etape, projet_id FROM workflow_sessions WHERE id = %(id)s",
        {"id": session_id},
    )
    ligne = curseur.fetchone()
    if ligne is None:
        return None
    curseur.execute(
        "SELECT id, texte, origine, statut, statut_propose, justification_proposee "
        "FROM workflow_hypotheses WHERE session_id = %(id)s ORDER BY id",
        {"id": session_id},
    )
    hypotheses = [
        Hypothese(
            id=h[0],
            texte=h[1],
            origine=h[2],
            statut=h[3],
            statut_propose=h[4],
            justification_proposee=h[5],
        )
        for h in curseur.fetchall()
    ]
    return EtatSession(
        id=ligne[0],
        etape=ligne[1],
        projet_id=ligne[2],
        hypotheses=hypotheses,
        nb_en_attente=sum(1 for h in hypotheses if h.statut == "en_attente"),
    )


@router.post("/workflows", status_code=201)
def creer_session(entree: SessionEntree, connexion: Connexion) -> EtatSession:
    with connexion.cursor() as curseur:
        curseur.execute(
            "INSERT INTO workflow_sessions (projet_id, feature) "
            "VALUES (%(projet_id)s, %(feature)s) RETURNING id",
            {"projet_id": entree.projet_id, "feature": entree.feature},
        )
        session_id = curseur.fetchone()[0]
        curseur.execute(
            "INSERT INTO workflow_messages (session_id, role, etape, contenu) "
            "VALUES (%(id)s, 'po', %(etape)s, %(contenu)s)",
            {"id": session_id, "etape": ETAPES[0], "contenu": entree.feature},
        )
        # Les [HYPOTHÈSE À VALIDER] déjà présentes dans la Feature collée entrent
        # au registre dès l'étape 0 (jamais perdues, A8) — dédupliquées par clé
        # normalisée, comme dans le moteur.
        cles_vues: set[str] = set()
        for texte in extraire_hypotheses(entree.feature):
            cle = cle_hypothese(texte)
            if cle in cles_vues:
                continue
            cles_vues.add(cle)
            curseur.execute(
                "INSERT INTO workflow_hypotheses (session_id, texte, origine) "
                "VALUES (%(id)s, %(texte)s, 'po')",
                {"id": session_id, "texte": texte},
            )
        etat = _lire_session(curseur, session_id)
    connexion.commit()
    return etat


class SessionResume(BaseModel):
    id: int
    etape: str
    projet_id: int | None
    apercu_feature: str


@router.get("/workflows")
def lister_sessions(connexion: Connexion) -> list[SessionResume]:
    """Liste des sessions — l'accueil E4 permet de RETROUVER une session en cours.

    Constaté en session de validation (06/07/2026) : sans liste, une session
    perdue de vue ne se retrouve que par URL devinée.
    """
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT id, etape, projet_id, feature FROM workflow_sessions "
            "ORDER BY modifie_le DESC, id DESC"
        )
        return [
            SessionResume(
                id=ligne[0],
                etape=ligne[1],
                projet_id=ligne[2],
                apercu_feature=(ligne[3][:120] + "…") if len(ligne[3]) > 120 else ligne[3],
            )
            for ligne in curseur.fetchall()
        ]


@router.get("/workflows/{session_id}")
def lire_session(session_id: int, connexion: Connexion) -> EtatSession:
    with connexion.cursor() as curseur:
        etat = _lire_session(curseur, session_id)
    if etat is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
    return etat


class MessageFil(BaseModel):
    role: Literal["po", "assistant"]
    etape: str
    contenu: str


@router.get("/workflows/{session_id}/messages")
def lire_messages(session_id: int, connexion: Connexion) -> list[MessageFil]:
    """Le fil de la conversation — consommé par l'écran E4."""
    with connexion.cursor() as curseur:
        if _lire_session(curseur, session_id) is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "SELECT role, etape, contenu FROM workflow_messages "
            "WHERE session_id = %(id)s ORDER BY id",
            {"id": session_id},
        )
        return [
            MessageFil(role=ligne[0], etape=ligne[1], contenu=ligne[2])
            for ligne in curseur.fetchall()
        ]


@router.post("/workflows/{session_id}/avancer")
def valider_etape(session_id: int, entree: ValidationEntree, connexion: Connexion) -> EtatSession:
    """Validation Oui/Non de l'étape (règle 5). Ne lève AUCUNE hypothèse (A8)."""
    with connexion.cursor() as curseur:
        etat = _lire_session(curseur, session_id)
        if etat is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        nouvelle_etape = avancer(etat.etape, entree.valide)
        curseur.execute(
            "UPDATE workflow_sessions SET etape = %(etape)s, modifie_le = now() WHERE id = %(id)s",
            {"id": session_id, "etape": nouvelle_etape},
        )
        # Journal des Oui/Non (S2.10) : la part des « Non » sert de proxy v0
        # au taux d'édition de la télémétrie E4.4.
        curseur.execute(
            "INSERT INTO workflow_validations (session_id, etape, valide, commentaire) "
            "VALUES (%(id)s, %(etape)s, %(valide)s, %(commentaire)s)",
            {
                "id": session_id,
                "etape": etat.etape,
                "valide": entree.valide,
                "commentaire": entree.commentaire,
            },
        )
        if entree.commentaire:
            curseur.execute(
                "INSERT INTO workflow_messages (session_id, role, etape, contenu) "
                "VALUES (%(id)s, 'po', %(etape)s, %(contenu)s)",
                {"id": session_id, "etape": etat.etape, "contenu": entree.commentaire},
            )
        etat_apres = _lire_session(curseur, session_id)
    connexion.commit()
    return etat_apres


@router.post("/workflows/{session_id}/hypotheses", status_code=201)
def ajouter_hypothese(
    session_id: int, entree: HypotheseEntree, connexion: Connexion
) -> EtatSession:
    with connexion.cursor() as curseur:
        if _lire_session(curseur, session_id) is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "INSERT INTO workflow_hypotheses (session_id, texte, origine) "
            "VALUES (%(id)s, %(texte)s, %(origine)s)",
            {"id": session_id, "texte": entree.texte, "origine": entree.origine},
        )
        etat = _lire_session(curseur, session_id)
    connexion.commit()
    return etat


@router.post("/workflows/{session_id}/hypotheses/{hypothese_id}")
def decider_hypothese(
    session_id: int, hypothese_id: int, entree: DecisionEntree, connexion: Connexion
) -> EtatSession:
    """Décision INDIVIDUELLE et explicite — seul chemin qui lève une hypothèse (A8)."""
    with connexion.cursor() as curseur:
        curseur.execute(
            "UPDATE workflow_hypotheses SET statut = %(statut)s, decidee_le = now() "
            "WHERE id = %(hid)s AND session_id = %(sid)s RETURNING id",
            {"hid": hypothese_id, "sid": session_id, "statut": entree.statut},
        )
        if curseur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail=f"Hypothèse {hypothese_id} introuvable pour la session {session_id}",
            )
        etat = _lire_session(curseur, session_id)
    connexion.commit()
    return etat


class Synthese(BaseModel):
    etape: str
    hypotheses_non_levees: list[Hypothese]
    avertissement: str | None


@router.get("/workflows/{session_id}/synthese")
def synthese(session_id: int, connexion: Connexion) -> Synthese:
    """Récapitulatif d'étape 5 — transmis à l'export (E5, arbitrage A8)."""
    with connexion.cursor() as curseur:
        etat = _lire_session(curseur, session_id)
    if etat is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
    if not est_terminale(etat.etape):
        raise HTTPException(
            status_code=409,
            detail=f"La synthèse n'est disponible qu'à l'étape « {ETAPES[-1]} » "
            f"(étape courante : « {etat.etape} »)",
        )
    en_attente = [h for h in etat.hypotheses if h.statut == "en_attente"]
    return Synthese(
        etape=etat.etape,
        hypotheses_non_levees=en_attente,
        avertissement=(
            f"{len(en_attente)} hypothèse(s) non levée(s) — l'export reste autorisé "
            "mais ce récapitulatif doit l'accompagner (arbitrage A8)."
            if en_attente
            else None
        ),
    )
