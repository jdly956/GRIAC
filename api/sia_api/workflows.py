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
    titre: str | None = None  # nom libre (S3.13) — sinon l'aperçu de la Feature


@router.get("/workflows")
def lister_sessions(connexion: Connexion) -> list[SessionResume]:
    """Liste des sessions — l'accueil E4 permet de RETROUVER une session en cours.

    Constaté en session de validation (06/07/2026) : sans liste, une session
    perdue de vue ne se retrouve que par URL devinée. Les sessions archivées
    (S3.13) sont masquées — jamais supprimées.
    """
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT id, etape, projet_id, feature, titre FROM workflow_sessions "
            "WHERE NOT archivee ORDER BY modifie_le DESC, id DESC"
        )
        return [
            SessionResume(
                id=ligne[0],
                etape=ligne[1],
                projet_id=ligne[2],
                apercu_feature=(ligne[3][:120] + "…") if len(ligne[3]) > 120 else ligne[3],
                titre=ligne[4],
            )
            for ligne in curseur.fetchall()
        ]


class SessionMaj(BaseModel):
    titre: str | None = None
    archivee: bool | None = None


@router.patch("/workflows/{session_id}")
def gerer_session(session_id: int, entree: SessionMaj, connexion: Connexion) -> dict:
    """Renommer / archiver (S3.13) — l'archivage masque, ne détruit jamais."""
    champs = []
    parametres: dict = {"id": session_id}
    if entree.titre is not None:
        champs.append("titre = %(titre)s")
        parametres["titre"] = entree.titre.strip() or None
    if entree.archivee is not None:
        champs.append("archivee = %(archivee)s")
        parametres["archivee"] = entree.archivee
    if not champs:
        raise HTTPException(status_code=422, detail="Rien à modifier (titre ou archivee).")
    with connexion.cursor() as curseur:
        curseur.execute(
            f"UPDATE workflow_sessions SET {', '.join(champs)} "
            "WHERE id = %(id)s RETURNING id, titre, archivee",
            parametres,
        )
        ligne = curseur.fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
    connexion.commit()
    return {"id": ligne[0], "titre": ligne[1], "archivee": ligne[2]}


@router.get("/workflows/{session_id}")
def lire_session(session_id: int, connexion: Connexion) -> EtatSession:
    with connexion.cursor() as curseur:
        etat = _lire_session(curseur, session_id)
    if etat is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
    return etat


class TraceSource(BaseModel):
    nom: str
    section: str
    extrait: str  # l'extrait EXACT du chunk cité (A3, S3.9)


class MessageFil(BaseModel):
    role: Literal["po", "assistant"]
    etape: str
    contenu: str
    sources: list[TraceSource] = []
    avertissements: list[str] = []
    divergences: list[str] = []


@router.get("/workflows/{session_id}/messages")
def lire_messages(session_id: int, connexion: Connexion) -> list[MessageFil]:
    """Le fil de la conversation, avec sa traçabilité persistée (S3.9/A3)."""
    with connexion.cursor() as curseur:
        if _lire_session(curseur, session_id) is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "SELECT id, role, etape, contenu FROM workflow_messages "
            "WHERE session_id = %(id)s ORDER BY id",
            {"id": session_id},
        )
        lignes = curseur.fetchall()
        curseur.execute(
            "SELECT t.message_id, t.type, t.nom, t.section, t.extrait, t.contenu "
            "FROM message_traces t JOIN workflow_messages m ON m.id = t.message_id "
            "WHERE m.session_id = %(id)s ORDER BY t.id",
            {"id": session_id},
        )
        traces: dict[int, dict[str, list]] = {}
        for message_id, type_trace, nom, section, extrait, contenu in curseur.fetchall():
            par_message = traces.setdefault(
                message_id, {"sources": [], "avertissements": [], "divergences": []}
            )
            if type_trace == "source":
                par_message["sources"].append(
                    TraceSource(nom=nom or "", section=section or "", extrait=extrait or "")
                )
            elif type_trace == "avertissement":
                par_message["avertissements"].append(contenu or "")
            else:
                par_message["divergences"].append(contenu or "")
        return [
            MessageFil(
                role=ligne[1],
                etape=ligne[2],
                contenu=ligne[3],
                **traces.get(ligne[0], {}),
            )
            for ligne in lignes
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


# Enregistrée AVANT /hypotheses/{hypothese_id} : « appliquer-propositions »
# serait sinon capté par le paramètre dynamique.
@router.post("/workflows/{session_id}/hypotheses/appliquer-propositions")
def appliquer_levees_proposees(session_id: int, connexion: Connexion) -> EtatSession:
    """S3.21 : applique EN LOT les levées proposées par le moteur (S2.13).

    Arbitrage du 07/07/2026 (session 12 : 16 hypothèses en attente en fin de
    session) : le PO relit la liste des propositions à l'écran et les applique
    d'un clic — la décision reste la sienne, en lot. L'esprit d'A8 tient :
    seules les hypothèses portant une PROPOSITION du moteur sont touchées,
    jamais une hypothèse sans proposition, jamais de levée silencieuse.
    """
    with connexion.cursor() as curseur:
        if _lire_session(curseur, session_id) is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        curseur.execute(
            "UPDATE workflow_hypotheses SET statut = statut_propose, decidee_le = now() "
            "WHERE session_id = %(sid)s AND statut = 'en_attente' "
            "AND statut_propose IS NOT NULL RETURNING id",
            {"sid": session_id},
        )
        appliquees = curseur.fetchall()
        if not appliquees:
            raise HTTPException(
                status_code=409, detail="Aucune levée proposée à appliquer sur cette session."
            )
        etat = _lire_session(curseur, session_id)
    connexion.commit()
    return etat


@router.post("/workflows/{session_id}/hypotheses/{hypothese_id}")
def decider_hypothese(
    session_id: int, hypothese_id: int, entree: DecisionEntree, connexion: Connexion
) -> EtatSession:
    """Décision INDIVIDUELLE et explicite — chemin nominal de levée (A8).

    L'autre chemin (S3.21, ci-dessus) n'applique QUE des propositions relues.
    """
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
