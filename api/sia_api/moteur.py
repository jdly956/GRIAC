"""Moteur conversationnel du workflow — E3.2 (S2.6), le cœur du produit.

`POST /workflows/{id}/message` : le PO écrit dans le fil (réponse d'interview,
validation, correction OU question documentaire libre — arbitrage A2 : même
moteur, pas d'écran dédié). À chaque message, le moteur :

1. mobilise le RAG (`/contexte`, S2.4) — arbitrage A2 : à CHAQUE étape ;
2. assemble le prompt système : **prompt 3 intégral** (source unique S1.10)
   + étape courante + contexte/NFR du projet (E8, S1.11) + extraits cités
   + few-shot (gold si fourni, sinon repli silver JAMAIS présenté comme
   validé — CLAUDE.md) + consignes A3 (citation/origine) et A9 (divergences) ;
3. appelle Albert (`openweight-large`, max_tokens généreux — modèle à
   raisonnement, gotcha S1.5 ; réponse vide = erreur explicite) ;
4. verse le message PO et la réponse dans `workflow_messages`, extrait les
   [HYPOTHÈSE À VALIDER] nouvelles vers le registre (origine `modele`, A8) ;
5. restitue : réponse, sources mobilisées (panneau A3), hypothèses ajoutées,
   [DIVERGENCE] corpus↔PO relevées (A9, arbitrées par le PO), avertissements
   (règle 1, budget, aucune source, repli rerank) — jamais d'échec silencieux.
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sia_api.config import Settings
from sia_api.db import get_connexion
from sia_api.gabarit import extraire_stories_us
from sia_api.recherche import (
    RechercheEntree,
    SourceCitee,
    construire_contexte,
    get_albert,
)
from sia_api.workflow import extraire_hypotheses, verifier_lot_interview

router = APIRouter(tags=["moteur"])

CHEMIN_PROMPT3 = Path(__file__).parents[1] / "prompts" / "prompt-3-rediger-mes-user-stories.md"
DOSSIER_GOLD = Path(__file__).parents[2] / "evals" / "gold"
FICHIER_SILVER = Path(__file__).parents[2] / "evals" / "silver" / "stories-silver-candidates.md"

BUDGET_TOTAL_TOKENS = 20_000  # CLAUDE.md : gabarit + few-shot + chunks + brief
HISTORIQUE_MAX_MESSAGES = 8
MAX_TOKENS_REPONSE = 4096  # modèle à raisonnement : ne jamais brider trop bas (S1.5)
MARQUEUR_DIVERGENCE = "[DIVERGENCE]"


def estimer_tokens(texte: str) -> int:
    return max(1, len(texte) // 4)


def extraire_divergences(texte: str) -> list[str]:
    """Lignes [DIVERGENCE] corpus↔PO — signalées avec source, arbitrées par le PO (A9)."""
    return [ligne.strip() for ligne in texte.splitlines() if MARQUEUR_DIVERGENCE in ligne]


def charger_few_shot() -> tuple[str, str] | None:
    """(exemple, origine) — gold prioritaire ; repli silver jamais présenté comme validé."""
    if DOSSIER_GOLD.is_dir():
        for fichier in sorted(DOSSIER_GOLD.glob("*.md")):
            stories = extraire_stories_us(fichier.read_text(encoding="utf-8"))
            if stories:
                return stories[0], "gold"
    if FICHIER_SILVER.is_file():
        stories = extraire_stories_us(FICHIER_SILVER.read_text(encoding="utf-8"))
        if stories:
            return stories[0], "silver"
    return None


def construire_prompt_systeme(
    etape: str,
    projet: dict | None,
    contexte_cite: str,
    few_shot: tuple[str, str] | None,
) -> str:
    """Assemblage du prompt système — le prompt 3 reste la source unique du workflow."""
    blocs = [CHEMIN_PROMPT3.read_text(encoding="utf-8"), "\n---\n## CONTEXTE DE SESSION (SIA PO)"]
    blocs.append(
        f"Étape courante du workflow : **{etape}**. Reste dans cette étape tant que le PO "
        "n'a pas validé (règle 5) ; c'est l'application qui gère les transitions."
    )
    if projet:
        blocs.append(f"Projet : {projet['nom']} — {projet['contexte']}")
        if projet["nfrs"]:
            blocs.append(
                "NFR du projet (à mobiliser pour pré-remplir le bloc G de l'interview "
                "et les CA transverses — E8) :"
            )
            blocs += [
                f"- {nfr['type']} : {nfr['formulation']}"
                + (f" (cible : {nfr['valeur_cible']})" if nfr["valeur_cible"] else "")
                for nfr in projet["nfrs"]
            ]
    blocs.append("## EXTRAITS DU CORPUS DOCUMENTAIRE (mobilisés par le RAG)")
    blocs.append(
        contexte_cite
        if contexte_cite
        else "AUCUNE source récupérable pour ce message : dis-le explicitement au PO et "
        "marque [HYPOTHÈSE À VALIDER] tout contenu que tu proposes (anti-invention)."
    )
    blocs.append(
        "## CONSIGNES DE TRAÇABILITÉ (SIA PO)\n"
        "- Toute affirmation issue des extraits cite sa source : "
        "« [Source : nom — section] » (A3).\n"
        "- Toute information ne venant ni des extraits ni du PO est marquée "
        "[HYPOTHÈSE À VALIDER].\n"
        "- Si une affirmation du PO contredit un extrait cité, signale-le sur une ligne "
        f"commençant par {MARQUEUR_DIVERGENCE} avec la source — c'est le PO qui arbitre (A9)."
    )
    if few_shot:
        exemple, origine = few_shot
        avertissement = (
            "exemple GOLD validé"
            if origine == "gold"
            else "exemple SILVER : candidate NON VALIDÉE, repli provisoire — ne la présente "
            "jamais comme une référence validée, ses [HYPOTHÈSE À VALIDER] le restent"
        )
        blocs.append(f"## EXEMPLE DE FORMAT ({avertissement})\n{exemple}")
    return "\n\n".join(blocs)


class MessageEntree(BaseModel):
    message: str = Field(min_length=1)


class MessageResultat(BaseModel):
    reponse: str
    etape: str
    sources: list[SourceCitee]  # panneau « sources mobilisées » (A3)
    hypotheses_ajoutees: list[str]
    divergences: list[str]  # A9 — arbitrées par le PO
    avertissements: list[str]


Connexion = Annotated[Any, Depends(get_connexion)]
Albert = Annotated[tuple[Any, Settings], Depends(get_albert)]


@router.post("/workflows/{session_id}/message")
def message_route(
    session_id: int, entree: MessageEntree, connexion: Connexion, albert: Albert
) -> MessageResultat:
    client, settings = albert
    avertissements: list[str] = []

    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT etape, projet_id, feature FROM workflow_sessions WHERE id = %(id)s",
            {"id": session_id},
        )
        session = curseur.fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} introuvable")
        etape, projet_id, feature = session

        projet = None
        if projet_id is not None:
            curseur.execute(
                "SELECT nom, contexte FROM projects WHERE id = %(id)s", {"id": projet_id}
            )
            ligne = curseur.fetchone()
            if ligne:
                curseur.execute(
                    "SELECT type, formulation, valeur_cible FROM project_nfrs "
                    "WHERE project_id = %(id)s ORDER BY id",
                    {"id": projet_id},
                )
                projet = {
                    "nom": ligne[0],
                    "contexte": ligne[1],
                    "nfrs": [
                        {"type": n[0], "formulation": n[1], "valeur_cible": n[2]}
                        for n in curseur.fetchall()
                    ],
                }

        curseur.execute(
            "SELECT role, contenu FROM workflow_messages WHERE session_id = %(id)s "
            "ORDER BY id DESC LIMIT %(limite)s",
            {"id": session_id, "limite": HISTORIQUE_MAX_MESSAGES},
        )
        historique = list(reversed(curseur.fetchall()))

        # A2 : le RAG est mobilisé à chaque étape, question libre comprise.
        contexte = construire_contexte(
            connexion,
            client,
            settings,
            RechercheEntree(question=entree.message, projet_id=projet_id),
        )
        if contexte.avertissement:
            avertissements.append(contexte.avertissement)

        prompt_systeme = construire_prompt_systeme(
            etape, projet, contexte.contexte, charger_few_shot()
        )
        messages = [{"role": "system", "content": prompt_systeme}]
        messages.append({"role": "user", "content": f"Feature de la session :\n{feature}"})
        messages += [
            {"role": "user" if role == "po" else "assistant", "content": contenu}
            for role, contenu in historique
        ]
        messages.append({"role": "user", "content": entree.message})

        total_estime = estimer_tokens("".join(m["content"] for m in messages))
        if total_estime > BUDGET_TOTAL_TOKENS:
            avertissements.append(
                f"Budget de contexte dépassé (~{total_estime} tokens estimés > "
                f"{BUDGET_TOTAL_TOKENS}) — à surveiller (E6)."
            )

        reponse_llm = client.chat.completions.create(
            model=settings.albert_model_chat,
            messages=messages,
            max_tokens=MAX_TOKENS_REPONSE,
        )
        choix = reponse_llm.choices[0]
        contenu_reponse = (choix.message.content or "").strip()
        if not contenu_reponse:
            raise HTTPException(
                status_code=502,
                detail=f"Réponse vide du modèle (finish_reason={choix.finish_reason}) — "
                "voir le gotcha modèles à raisonnement (S1.5).",
            )

        # Règle 1 : signalée, jamais bloquée silencieusement.
        if etape == "interview":
            avertissements += verifier_lot_interview(contenu_reponse)

        curseur.execute(
            "INSERT INTO workflow_messages (session_id, role, etape, contenu) "
            "VALUES (%(id)s, 'po', %(etape)s, %(contenu)s)",
            {"id": session_id, "etape": etape, "contenu": entree.message},
        )
        curseur.execute(
            "INSERT INTO workflow_messages (session_id, role, etape, contenu) "
            "VALUES (%(id)s, 'assistant', %(etape)s, %(contenu)s)",
            {"id": session_id, "etape": etape, "contenu": contenu_reponse},
        )

        curseur.execute(
            "SELECT texte FROM workflow_hypotheses WHERE session_id = %(id)s",
            {"id": session_id},
        )
        deja_connues = {ligne[0] for ligne in curseur.fetchall()}
        hypotheses_ajoutees = []
        for texte in extraire_hypotheses(contenu_reponse):
            if texte not in deja_connues:
                curseur.execute(
                    "INSERT INTO workflow_hypotheses (session_id, texte, origine) "
                    "VALUES (%(id)s, %(texte)s, 'modele')",
                    {"id": session_id, "texte": texte},
                )
                hypotheses_ajoutees.append(texte)
                deja_connues.add(texte)

    connexion.commit()
    return MessageResultat(
        reponse=contenu_reponse,
        etape=etape,
        sources=contexte.sources,
        hypotheses_ajoutees=hypotheses_ajoutees,
        divergences=extraire_divergences(contenu_reponse),
        avertissements=avertissements,
    )
