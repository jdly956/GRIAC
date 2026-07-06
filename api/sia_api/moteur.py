"""Moteur conversationnel du workflow — E3.2 (S2.6), le cœur du produit.

`POST /workflows/{id}/message` : le PO écrit dans le fil (réponse d'interview,
validation, correction OU question documentaire libre — arbitrage A2 : même
moteur, pas d'écran dédié). À chaque message, le moteur :

1. mobilise le RAG (`/contexte`, S2.4) — arbitrage A2 : à CHAQUE étape ;
2. assemble le prompt système : **prompt 3 intégral** (source unique S1.10)
   + étape courante + contexte/NFR du projet (E8, S1.11) + extraits cités
   + few-shot (gold si fourni, sinon repli silver JAMAIS présenté comme
   validé — CLAUDE.md) + consignes A3 (citation/origine) et A9 (divergences) ;
3. appelle Albert (modèle `ALBERT_MODEL_CHAT` — défaut `openweight-medium`,
   verdict E6 v0 ; max_tokens généreux — gotcha raisonnement S1.5, toujours
   valable si retour à `openweight-large` ; réponse vide = erreur explicite) ;
4. verse le message PO et la réponse dans `workflow_messages`, extrait les
   [HYPOTHÈSE À VALIDER] nouvelles vers le registre (origine `modele`, A8) ;
   quand un message du PO tranche une hypothèse déjà en attente, le moteur
   émet [LEVÉE PROPOSÉE : #id — confirmée|rejetée — justification] : la
   proposition est persistée SANS toucher le statut — la décision individuelle
   du PO reste le seul chemin de levée (rapprochement interview↔registre, A8) ;
5. restitue : réponse, sources mobilisées (panneau A3), hypothèses ajoutées,
   levées proposées, [DIVERGENCE] corpus↔PO relevées (A9, arbitrées par le PO),
   avertissements (règle 1, budget, aucune source, repli rerank) — jamais
   d'échec silencieux.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sia_api.config import Settings
from sia_api.db import get_connexion
from sia_api.gabarit import extraire_stories_us, titre_us, valider_dor, valider_us
from sia_api.parametres import lire_surcharge_modele
from sia_api.recherche import (
    RechercheEntree,
    SourceCitee,
    construire_contexte,
    get_albert,
)
from sia_api.workflow import (
    cle_hypothese,
    est_doublon_hypothese,
    extraire_hypotheses,
    extraire_levees_proposees,
    verifier_lot_interview,
)

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


ETAPES_AVEC_STORIES = ("redaction", "controle_dor", "synthese")


def _titre_us(story: str) -> str:
    return titre_us(story) or "(sans titre)"


def _extraire_tableau_dor(contenu: str) -> str:
    """Isole le tableau DoR : un message d'étape 4 contient aussi des tableaux de CA."""
    lignes = contenu.splitlines()
    debut = next(
        (
            i
            for i, ligne in enumerate(lignes)
            if ligne.strip().startswith("|") and "critère dor" in ligne.lower()
        ),
        None,
    )
    if debut is None:
        return ""
    fin = debut
    while fin < len(lignes) and lignes[fin].strip().startswith("|"):
        fin += 1
    return "\n".join(lignes[debut:fin])


def controler_conformite(etape: str, contenu: str) -> list[str]:
    """Contrôle automatisé S1.10 en sortie des étapes de production (E3, DoR auto).

    - étapes rédaction/contrôle DoR/synthèse : chaque US extraite passe par
      `valider_us` (le modèle s'auto-contrôle mal — le validateur tranche) ;
    - un tableau DoR présent dans N'IMPORTE quelle étape de production passe
      par `valider_dor` (10 critères, statuts, « estimée en refinement »
      toujours 🔵) — constaté session 9 (06/07/2026) : le cycle réel est
      « une story = rédaction + DoR » et la machine à états file à `synthese`
      pendant que les DoR continuent d'arriver ; conditionner à la seule
      étape `controle_dor` laissait ces tableaux sans contrôle. L'ABSENCE de
      tableau ne se signale qu'à l'étape contrôle DoR (ailleurs elle est
      normale).
    Signalé au PO dans les avertissements, jamais bloquant : c'est lui qui
    valide ou itère (règle 5).
    """
    rapports: list[str] = []
    if etape in ETAPES_AVEC_STORIES:
        for story in extraire_stories_us(contenu):
            rapport = valider_us(story)
            if not rapport.conforme:
                rapports.append(
                    f"Contrôle gabarit (S1.10) — US « {_titre_us(story)} » non conforme : "
                    + " ; ".join(rapport.violations)
                )
        tableau_dor = _extraire_tableau_dor(contenu)
        if tableau_dor or etape == "controle_dor":
            rapport_dor = valider_dor(tableau_dor)
            if not rapport_dor.conforme:
                rapports.append("Contrôle DoR automatisé : " + " ; ".join(rapport_dor.violations))
    return rapports


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
    hypotheses_en_attente: Sequence[tuple[int, str]] = (),
) -> str:
    """Assemblage du prompt système — le prompt 3 reste la source unique du workflow."""
    blocs = [CHEMIN_PROMPT3.read_text(encoding="utf-8"), "\n---\n## CONTEXTE DE SESSION (SIA PO)"]
    blocs.append(
        f"Étape courante du workflow : **{etape}**. Reste dans cette étape tant que le PO "
        "n'a pas validé (règle 5) ; c'est l'application qui gère les transitions. "
        "Ne demande JAMAIS de validation dans le texte (pas de « Cette version vous "
        "convient-elle ? (Oui / Non) ») : l'interface fournit les boutons Oui/Non de la "
        "règle 5 — termine tes messages sur le contenu."
    )
    if etape in ("redaction", "controle_dor"):
        # Arbitrage S3.2 (06/07/2026) : le cycle réel est « une story = rédaction
        # + contrôle DoR » — l'UI fournit un bouton « Story suivante ». Une story
        # à la fois évite aussi la troncature à MAX_TOKENS (constat session 8).
        blocs.append(
            "Travaille UNE SEULE story à la fois : sa rédaction complète puis son "
            "contrôle DoR. N'enchaîne JAMAIS spontanément sur la story suivante — "
            "l'interface fournit un bouton « Story suivante ». Après chaque story, "
            "indique combien de stories candidates restent à rédiger ; s'il n'en "
            "reste aucune, dis-le explicitement (le PO validera l'étape)."
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
        "[HYPOTHÈSE À VALIDER]. En particulier toute VALEUR CHIFFRÉE inventée "
        "(délai, seuil, volumétrie, durée de rétention, horaire de job, "
        "performance) porte le marqueur sur sa ligne.\n"
        "- Utilise EXACTEMENT le marqueur [HYPOTHÈSE À VALIDER] — jamais de "
        "variante ([HYPOTHÈSE 1 A], [HYPOTHÈSE À VALIDER 1], « Hypothèse A1 »…) : "
        "les variantes n'entrent pas au registre et se perdent.\n"
        "- Quand tu proposes des ALTERNATIVES au choix du PO (option A / B / C), "
        "ne les marque pas : seule l'option retenue par le PO deviendra, si "
        "besoin, une [HYPOTHÈSE À VALIDER].\n"
        "- Ne re-liste pas dans tes récapitulatifs les hypothèses déjà "
        "enregistrées au registre — elles y sont, le PO les voit.\n"
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
    # En DERNIÈRE position du prompt (la plus saillante) : constaté session 9
    # (06/07/2026), la consigne noyée en milieu de prompt n'a pas été suivie —
    # le PO a tranché une hypothèse sans qu'aucune levée ne soit proposée.
    if hypotheses_en_attente:
        registre = "\n".join(f"- #{hid} : {texte}" for hid, texte in hypotheses_en_attente)
        blocs.append(
            "## REGISTRE DES HYPOTHÈSES EN ATTENTE (A8)\n"
            f"{registre}\n"
            "IMPÉRATIF — à vérifier À CHAQUE réponse : si le dernier message du PO ou un "
            "extrait cité tranche l'une de ces hypothèses, termine ta réponse par une ligne "
            "dédiée, exactement sous cette forme :\n"
            "[LEVÉE PROPOSÉE : #<numéro> — confirmée|rejetée — justification courte]\n"
            "Exemple : « [LEVÉE PROPOSÉE : #7 — confirmée — le PO a confirmé que l'équipe "
            "crée le jeu de données] ». "
            "C'est une PROPOSITION : seul le PO confirme ou rejette dans le registre (A8) — "
            "ne considère jamais une hypothèse comme levée de toi-même. "
            "Ne re-marque pas ces hypothèses déjà enregistrées avec [HYPOTHÈSE À VALIDER]."
        )
    return "\n\n".join(blocs)


class MessageEntree(BaseModel):
    message: str = Field(min_length=1)


class LeveeProposeeSortie(BaseModel):
    """Proposition de levée émise par le moteur — la décision reste au PO (A8)."""

    hypothese_id: int
    statut_propose: Literal["confirmee", "rejetee"]
    justification: str


class MessageResultat(BaseModel):
    reponse: str
    etape: str
    sources: list[SourceCitee]  # panneau « sources mobilisées » (A3)
    hypotheses_ajoutees: list[str]
    levees_proposees: list[LeveeProposeeSortie]  # rapprochement interview↔registre (A8)
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

        # S3.12 : le modèle de chat est surchargeable depuis l'écran Paramètres
        # (table parametres) SANS relance — surcharge UI > env/défaut (S2.14).
        modele_chat = lire_surcharge_modele(curseur) or settings.albert_model_chat

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

        # Registre lu AVANT l'appel : les hypothèses en attente entrent au prompt
        # (rapprochement interview↔registre) et l'ensemble sert à la déduplication.
        curseur.execute(
            "SELECT id, texte, statut FROM workflow_hypotheses "
            "WHERE session_id = %(id)s ORDER BY id",
            {"id": session_id},
        )
        registre = curseur.fetchall()
        hypotheses_en_attente = [(h[0], h[1]) for h in registre if h[2] == "en_attente"]

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
            etape, projet, contexte.contexte, charger_few_shot(), hypotheses_en_attente
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
            model=modele_chat,
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

        # S3.11 : chaque appel chat verse son usage au registre de consommation
        # (jauge vs quota tpd 2,46 M — S1.5). Absent du retour = rien à verser.
        usage = getattr(reponse_llm, "usage", None)
        if usage is not None:
            curseur.execute(
                "INSERT INTO conso_tokens (source, session_id, modele, tokens_entree, "
                "tokens_sortie) VALUES ('chat', %(id)s, %(modele)s, %(entree)s, %(sortie)s)",
                {
                    "id": session_id,
                    "modele": modele_chat,
                    "entree": getattr(usage, "prompt_tokens", 0) or 0,
                    "sortie": getattr(usage, "completion_tokens", 0) or 0,
                },
            )

        # Règle 1 : signalée, jamais bloquée silencieusement.
        if etape == "interview":
            avertissements += verifier_lot_interview(contenu_reponse)

        # Contrôle DoR/gabarit automatisé (E3) : signalé, le PO arbitre (règle 5).
        avertissements += controler_conformite(etape, contenu_reponse)

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

        # Déduplication à deux étages : clé normalisée (décoration markdown)
        # puis rapprochement sémantique (S2.15) — les récapitulatifs du modèle
        # re-listent les hypothèses sous d'autres mots (session 11).
        textes_connus = [h[1] for h in registre]
        deja_connues = {cle_hypothese(t) for t in textes_connus}
        hypotheses_ajoutees = []
        for texte in extraire_hypotheses(contenu_reponse):
            cle = cle_hypothese(texte)
            if cle in deja_connues or est_doublon_hypothese(texte, textes_connus):
                continue
            curseur.execute(
                "INSERT INTO workflow_hypotheses (session_id, texte, origine) "
                "VALUES (%(id)s, %(texte)s, 'modele')",
                {"id": session_id, "texte": texte},
            )
            hypotheses_ajoutees.append(texte)
            deja_connues.add(cle)
            textes_connus.append(texte)

        # Rapprochement interview↔registre (A8) : la proposition est persistée
        # sur ses colonnes dédiées — le statut n'est JAMAIS modifié ici, la
        # décision individuelle du PO reste le seul chemin de levée.
        levees = extraire_levees_proposees(
            contenu_reponse, {hid for hid, _ in hypotheses_en_attente}
        )
        for levee in levees:
            curseur.execute(
                "UPDATE workflow_hypotheses SET statut_propose = %(statut_propose)s, "
                "justification_proposee = %(justification)s, proposee_le = now() "
                "WHERE id = %(hid)s AND session_id = %(sid)s AND statut = 'en_attente'",
                {
                    "statut_propose": levee.statut_propose,
                    "justification": levee.justification,
                    "hid": levee.hypothese_id,
                    "sid": session_id,
                },
            )

    connexion.commit()
    return MessageResultat(
        reponse=contenu_reponse,
        etape=etape,
        sources=contexte.sources,
        hypotheses_ajoutees=hypotheses_ajoutees,
        levees_proposees=[
            LeveeProposeeSortie(
                hypothese_id=levee.hypothese_id,
                statut_propose=levee.statut_propose,
                justification=levee.justification,
            )
            for levee in levees
        ],
        divergences=extraire_divergences(contenu_reponse),
        avertissements=avertissements,
    )
