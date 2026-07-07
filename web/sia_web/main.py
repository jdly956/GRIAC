"""Interface web du SIA PO — conversation (E4.1, S2.8), écrans projets et
« mes documents » (E4.2/E4.3, S2.9).

Front volontairement simple (CLAUDE.md) : formulaires HTML classiques en socle,
enrichis par htmx en fragments ciblés (R3/H7 : un POST htmx ajoute les bulles au
fil et met à jour rail/stepper/conso en out-of-band ; sans JavaScript, les mêmes
routes rendent la page complète — repli H14). Le DSFR (CSS + JS) est chargé par
CDN au MVP (à vendorer pour la prod, E7) avec des styles de repli locaux : la
page reste utilisable hors ligne.

Préfixe de chemin : les LIENS portent le `root_path` ASGI (`{{ racine }}`
dans les templates), pour servir l'app derrière un proxy à préfixe — cas
constaté sur pod Onyxia (03/07/2026) : le port 8081 n'est pas exposable
(RBAC), l'UI passe par le proxy code-server `/proxy/8081/` où les chemins
absolus cassaient la navigation. Les REDIRECTIONS, elles, partent sans
préfixe : code-server réécrit les Location en pré-ajoutant /proxy/8081
(voir `_rediriger`). Lancement : `uvicorn --root-path /proxy/8081 …` ; à la
racine (prod Helm, dev compose), root_path vide = comportement inchangé.
"""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

from sia_web import api_client

app = FastAPI(title="SIA PO — Web")

# S3.8 : htmx VENDORÉ (le CDN externe serait un point de fragilité — et la
# politique réseau des environnements le bloque) ; servi par l'app elle-même.
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


def _contexte_racine(request: Request) -> dict[str, str]:
    """`{{ racine }}` : root_path ASGI sans slash final ("" à la racine)."""
    return {"racine": request.scope.get("root_path", "").rstrip("/")}


# R1 (socle DSFR) : entrée active de la navigation, déduite du chemin
# APPLICATIF (scope["path"] ne porte pas le root_path — cohérent avec le
# proxy à préfixe du pod, cf. docstring du module).
_NAV_PREFIXES = [
    ("/projets", "projets"),
    ("/documents", "documents"),
    # R10 (UX9) : télémétrie + paramètres fusionnés sous « Suivi & réglages ».
    ("/suivi", "suivi"),
    ("/telemetrie", "suivi"),
    ("/parametres", "suivi"),
    ("/sessions", "sessions"),
]


def _contexte_navigation(request: Request) -> dict[str, str]:
    chemin = request.scope.get("path", "/")
    if chemin == "/":
        return {"nav_actif": "sessions"}
    for prefixe, entree in _NAV_PREFIXES:
        if chemin.startswith(prefixe):
            return {"nav_actif": entree}
    return {"nav_actif": ""}


# S3.6 : rendu serveur des messages du moteur — le PO lisait le markdown BRUT
# (tableaux Gherkin en pipes, constaté sessions 9/11). `html=False` : tout HTML
# présent dans la source est échappé (le contenu vient du LLM — jamais de HTML
# interprété) ; `breaks=True` : les retours à la ligne simples restent visibles
# (comportement du pre-wrap remplacé).
_markdown = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable("table")


def rendre_markdown(texte: str) -> str:
    return _markdown.render(texte or "")


templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates"),
    context_processors=[_contexte_racine, _contexte_navigation],
)
templates.env.filters["markdown"] = rendre_markdown


def _rediriger(request: Request, chemin: str) -> RedirectResponse:
    """Redirection 303 SANS préfixe root_path — asymétrie voulue avec les liens.

    Constaté sur pod Onyxia (03/07/2026, navigation privée à l'appui) : le
    proxy code-server réécrit les en-têtes Location en pré-ajoutant
    /proxy/8081 — un Location déjà préfixé ressort doublé
    (/proxy/8081/proxy/8081/…). Les corps HTML ne sont PAS réécrits, d'où
    les liens qui gardent {{ racine }}. À la racine (prod Helm, compose),
    un Location sans préfixe est déjà correct.
    """
    del request  # signature homogène avec les autres helpers ; préfixe volontairement omis
    return RedirectResponse(chemin, status_code=303)


ETAPES_LIBELLES = {
    "recuperation_feature": "0 — Récupération de la Feature",
    "interview": "1 — Interview de refinement",
    "stories_candidates": "2 — Stories candidates",
    "redaction": "3 — Rédaction des stories",
    "controle_dor": "4 — Contrôle DoR",
    "synthese": "5 — Synthèse finale",
}

# R2 : ordre des étapes pour le stepper DSFR de la barre de session (A5/H8).
ETAPES_ORDRE = list(ETAPES_LIBELLES)

# Les 7 types de NFR de l'entité Projet (E8/D19) — mêmes valeurs que l'api.
TYPES_NFR = [
    "performance",
    "volumetrie",
    "ssi",
    "rgpd",
    "accessibilite_rgaa",
    "disponibilite",
    "auditabilite",
]

# Statuts de parsing (S1.8) → libellés de l'écran « mes documents » (A5).
STATUTS_PARSING_LIBELLES = {
    "a_parser": "en attente",
    "parse": "indexé",
    "echec": "échec",
    "ocr_requis": "OCR requis",
}

# Sous ce ratio parsés/parsables, l'écran affiche l'alerte « couverture faible » (A5).
SEUIL_COUVERTURE = 0.8


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _page_erreur(request: Request, statut: int, corps: dict) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="erreur.html",
        context={"detail": corps.get("detail", "erreur inconnue")},
        status_code=statut if statut != 599 else 502,
    )


def _contexte_session(session_id: int) -> tuple[int, dict, dict | None]:
    """R3 : contexte commun à l'écran complet et au fragment htmx (hors fil)."""
    statut_etat, etat = api_client.appeler("GET", f"/workflows/{session_id}")
    if statut_etat != 200:
        return statut_etat, etat, None
    _, stories = api_client.appeler("GET", f"/workflows/{session_id}/stories")
    statut_conso, conso = api_client.appeler("GET", f"/workflows/{session_id}/conso")
    statut_parametres, parametres = api_client.appeler("GET", "/parametres")
    statut_contenus, stories_contenus = api_client.appeler(
        "GET", f"/workflows/{session_id}/stories/contenus"
    )
    # Compteur des levées proposées (S2.13) en attente de décision du PO.
    nb_levees_a_decider = sum(
        1
        for h in etat.get("hypotheses", [])
        if h.get("statut") == "en_attente" and h.get("statut_propose")
    )
    # R2 : panneau Stories du rail — contenus S3.13 en priorité, sinon repli
    # sur les seuls titres (l'endpoint contenus peut manquer, jamais bloquant).
    stories_affichees = stories_contenus if statut_contenus == 200 and stories_contenus else []
    if not stories_affichees and isinstance(stories, list):
        stories_affichees = [{"titre": t, "contenu": "", "editee": False} for t in stories]
    contexte = {
        "etat": etat,
        "libelle_etape": ETAPES_LIBELLES.get(etat["etape"], etat["etape"]),
        "etape_index": (ETAPES_ORDRE.index(etat["etape"]) if etat["etape"] in ETAPES_ORDRE else 0),
        "etapes_total": len(ETAPES_ORDRE),
        "nb_levees_a_decider": nb_levees_a_decider,
        # S3.11 : conso de la session (None si l'api ne répond pas — simple
        # indication, jamais bloquant). S3.12 : le PO sait quel modèle écrit.
        "conso": conso if statut_conso == 200 else None,
        "modele_actif": parametres.get("modele_actif") if statut_parametres == 200 else None,
        "stories_affichees": stories_affichees,
    }
    return 200, etat, contexte


def _construire_message_assistant(dernier_resultat: dict, etape_defaut: str) -> dict:
    """R2 (UX6) : le résultat d'un POST devient une bulle du fil ; les signaux
    A8 (hypothèses ajoutées, levées proposées) rejoignent ses avertissements."""
    notices = list(dernier_resultat.get("avertissements") or [])
    if dernier_resultat.get("hypotheses_ajoutees"):
        notices.append(
            f"{len(dernier_resultat['hypotheses_ajoutees'])} hypothèse(s) ajoutée(s) "
            "au registre — à décider dans le panneau Hypothèses (A8)."
        )
    if dernier_resultat.get("levees_proposees"):
        notices.append(
            f"{len(dernier_resultat['levees_proposees'])} levée(s) d'hypothèse "
            "proposée(s) — la décision vous revient, panneau Hypothèses (A8)."
        )
    return {
        "role": "assistant",
        "etape": dernier_resultat.get("etape", etape_defaut),
        "contenu": dernier_resultat.get("reponse", ""),
        "sources": dernier_resultat.get("sources") or [],
        "avertissements": notices,
        "divergences": dernier_resultat.get("divergences") or [],
    }


def _page_session(
    request: Request,
    session_id: int,
    dernier_resultat: dict | None = None,
    erreur: str | None = None,
) -> HTMLResponse:
    statut, etat, contexte = _contexte_session(session_id)
    if contexte is None:
        return _page_erreur(request, statut, etat)
    _, messages = api_client.appeler("GET", f"/workflows/{session_id}/messages")
    messages = messages if isinstance(messages, list) else []
    # R2 (UX6) : le résultat d'un POST rejoint le BAS du fil comme un message —
    # sauf s'il y figure déjà (stack réelle : persisté par l'api, S3.9).
    dernier_message = None
    if dernier_resultat:
        deja_dans_fil = (
            bool(messages)
            and messages[-1].get("role") == "assistant"
            and messages[-1].get("contenu") == dernier_resultat.get("reponse")
        )
        if not deja_dans_fil:
            dernier_message = _construire_message_assistant(dernier_resultat, etat["etape"])
    # R2 (H6) : panneau « sources de la dernière réponse » — celles du POST,
    # sinon celles du dernier message assistant tracé (S3.9).
    sources_dernier = (dernier_resultat or {}).get("sources") or []
    if not sources_dernier:
        for message in reversed(messages):
            if message.get("role") == "assistant" and message.get("sources"):
                sources_dernier = message["sources"]
                break
    contexte.update(
        {
            "messages": messages,
            "dernier_message": dernier_message,
            "sources_dernier": sources_dernier,
            "erreur": erreur,
        }
    )
    return templates.TemplateResponse(request=request, name="session.html", context=contexte)


def _est_htmx(request: Request) -> bool:
    """R3 (H7) : un POST htmx reçoit un fragment ; le même POST sans JavaScript
    reçoit la page complète (repli H14)."""
    return request.headers.get("hx-request") == "true"


def _fragment_echange(
    request: Request,
    session_id: int,
    message_po: str | None = None,
    dernier_resultat: dict | None = None,
    erreur: str | None = None,
) -> HTMLResponse:
    """R3 (H7) : bulles ajoutées au fil + rail/stepper/conso en out-of-band.

    Sur erreur, seule l'alerte est ajoutée (pas d'OOB) : l'écran garde l'état
    du dernier succès — le prochain échange réussi resynchronise tout.
    """
    statut, etat, contexte = _contexte_session(session_id)
    if contexte is None:
        contexte = {"etat": None}
        erreur = erreur or etat.get("detail", "session introuvable")
    contexte.update(
        {
            "message_po": message_po,
            "dernier_message": (
                _construire_message_assistant(dernier_resultat, contexte["etat"]["etape"])
                if dernier_resultat and contexte.get("etat")
                else None
            ),
            "sources_dernier": (dernier_resultat or {}).get("sources") or [],
            "erreur": erreur,
        }
    )
    return templates.TemplateResponse(
        request=request, name="_fragment_echange.html", context=contexte
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    statut, projets = api_client.appeler("GET", "/projects")
    statut_sessions, sessions = api_client.appeler("GET", "/workflows")
    # R7 : compteur des archivées — le lien « voir les archivées » dit combien.
    statut_archivees, archivees = api_client.appeler("GET", "/workflows?archivees=true")
    erreur = None if statut == 200 else projets.get("detail")
    projets = projets if statut == 200 else []
    # R9 : les projets archivés gardent leur nom sur les lignes de session.
    statut_pa, projets_archives = api_client.appeler("GET", "/projects?archives=true")
    noms_projets = {p["id"]: p["nom"] for p in projets}
    if statut_pa == 200 and isinstance(projets_archives, list):
        noms_projets.update({p["id"]: f"{p['nom']} (archivé)" for p in projets_archives})
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "projets": projets,
            "sessions": sessions if statut_sessions == 200 else [],
            "noms_projets": noms_projets,
            "nb_archivees": (
                len(archivees) if statut_archivees == 200 and isinstance(archivees, list) else 0
            ),
            "libelles_etapes": ETAPES_LIBELLES,
            "erreur": erreur,
        },
    )


# Enregistrée avant la route dynamique /sessions/{session_id}.
@app.get("/sessions/archivees", response_class=HTMLResponse)
def sessions_archivees(request: Request) -> HTMLResponse:
    """R7 (UX8) : le versant archivé — consultation, désarchivage, suppression."""
    statut, archivees = api_client.appeler("GET", "/workflows?archivees=true")
    return templates.TemplateResponse(
        request=request,
        name="archivees.html",
        context={
            "sessions": archivees if statut == 200 and isinstance(archivees, list) else [],
            "libelles_etapes": ETAPES_LIBELLES,
        },
    )


@app.post("/sessions")
def creer_session(
    request: Request, feature: Annotated[str, Form()], projet_id: Annotated[str, Form()] = ""
) -> RedirectResponse:
    corps = {"feature": feature, "projet_id": int(projet_id) if projet_id else None}
    statut, session = api_client.appeler("POST", "/workflows", json=corps)
    if statut != 201:
        return _rediriger(request, "/")
    return _rediriger(request, f"/sessions/{session['id']}")


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
def voir_session(request: Request, session_id: int) -> HTMLResponse:
    return _page_session(request, session_id)


@app.post("/sessions/{session_id}/message", response_class=HTMLResponse)
def envoyer_message(
    request: Request, session_id: int, message: Annotated[str, Form()]
) -> HTMLResponse:
    statut, resultat = api_client.appeler(
        "POST", f"/workflows/{session_id}/message", json={"message": message}
    )
    if _est_htmx(request):
        if statut != 200:
            return _fragment_echange(request, session_id, erreur=resultat.get("detail"))
        return _fragment_echange(request, session_id, message_po=message, dernier_resultat=resultat)
    if statut != 200:
        return _page_session(request, session_id, erreur=resultat.get("detail"))
    return _page_session(request, session_id, dernier_resultat=resultat)


@app.post("/sessions/{session_id}/valider", response_class=HTMLResponse)
def valider_etape(
    request: Request,
    session_id: int,
    valide: Annotated[str, Form()],
    commentaire: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Règle 5 bouclée : la décision avance la machine à états PUIS est transmise
    au moteur, qui produit l'entrée de l'étape suivante (Oui) ou l'itération (Non).

    Constaté en session de validation (06/07/2026) : sans ce second appel, le
    bouton changeait l'état sans aucune interaction LLM — la machine à états
    filait à « synthèse » pendant que la conversation restait à la rédaction,
    et le PO validait en double (bouton + « oui » tapé dans le fil).
    """
    statut, resultat = api_client.appeler(
        "POST",
        f"/workflows/{session_id}/avancer",
        json={"valide": valide == "oui", "commentaire": commentaire},
    )
    if statut != 200:
        if _est_htmx(request):
            return _fragment_echange(request, session_id, erreur=resultat.get("detail"))
        return _page_session(request, session_id, erreur=resultat.get("detail"))
    message = (
        "Étape validée (Oui) — poursuis le workflow sur l'étape courante."
        if valide == "oui"
        else f"Étape non validée (Non) — itère sur cette étape en tenant compte de : {commentaire}"
    )
    statut_moteur, reponse_moteur = api_client.appeler(
        "POST", f"/workflows/{session_id}/message", json={"message": message}
    )
    if _est_htmx(request):
        if statut_moteur != 200:
            return _fragment_echange(request, session_id, erreur=reponse_moteur.get("detail"))
        return _fragment_echange(
            request, session_id, message_po=message, dernier_resultat=reponse_moteur
        )
    if statut_moteur != 200:
        return _page_session(request, session_id, erreur=reponse_moteur.get("detail"))
    return _page_session(request, session_id, dernier_resultat=reponse_moteur)


@app.post("/sessions/{session_id}/story-suivante", response_class=HTMLResponse)
def story_suivante(request: Request, session_id: int) -> HTMLResponse:
    """Arbitrage S3.2 (06/07/2026) : le cycle réel est « une story = rédaction +
    contrôle DoR » — ce bouton enchaîne sur la story suivante SANS toucher la
    machine à états (le « Oui — étape suivante » reste le geste explicite du PO
    quand toutes les stories sont couvertes ; badge A5 fidèle)."""
    message = (
        "Story validée — enchaîne sur la STORY SUIVANTE de la liste des "
        "candidates (rédaction complète puis contrôle DoR), sans changer d'étape. "
        "S'il ne reste aucune story à rédiger, dis-le explicitement."
    )
    statut, resultat = api_client.appeler(
        "POST", f"/workflows/{session_id}/message", json={"message": message}
    )
    if _est_htmx(request):
        if statut != 200:
            return _fragment_echange(request, session_id, erreur=resultat.get("detail"))
        return _fragment_echange(request, session_id, message_po=message, dernier_resultat=resultat)
    if statut != 200:
        return _page_session(request, session_id, erreur=resultat.get("detail"))
    return _page_session(request, session_id, dernier_resultat=resultat)


@app.post("/sessions/{session_id}/stories/edition")
def editer_story_web(
    request: Request,
    session_id: int,
    titre: Annotated[str, Form()],
    contenu: Annotated[str, Form()],
) -> RedirectResponse:
    """S3.13 : la version éditée est stockée et gagne à l'export."""
    api_client.appeler(
        "PUT",
        f"/workflows/{session_id}/stories/edition",
        json={"titre": titre, "contenu": contenu},
    )
    return _rediriger(request, f"/sessions/{session_id}")


@app.post("/sessions/{session_id}/gerer")
def gerer_session_web(
    request: Request,
    session_id: int,
    titre: Annotated[str, Form()] = "",
    archiver: Annotated[str, Form()] = "",
    desarchiver: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """S3.13 : renommer / archiver ; R7 : désarchiver depuis l'écran des archivées."""
    if desarchiver:
        api_client.appeler("PATCH", f"/workflows/{session_id}", json={"archivee": False})
        return _rediriger(request, "/sessions/archivees")
    if archiver:
        api_client.appeler("PATCH", f"/workflows/{session_id}", json={"archivee": True})
        return _rediriger(request, "/")
    api_client.appeler("PATCH", f"/workflows/{session_id}", json={"titre": titre})
    return _rediriger(request, f"/sessions/{session_id}")


@app.post("/sessions/{session_id}/supprimer")
def supprimer_session_web(request: Request, session_id: int) -> RedirectResponse:
    """R6 (UX8) : suppression définitive — confirmée à l'écran, cascade en base."""
    api_client.appeler("DELETE", f"/workflows/{session_id}")
    return _rediriger(request, "/")


@app.post("/sessions/{session_id}/hypotheses/appliquer-propositions")
def appliquer_levees_proposees(request: Request, session_id: int) -> RedirectResponse:
    """S3.21 : applique en lot les levées proposées relues par le PO (A8 assoupli, arbitré)."""
    api_client.appeler("POST", f"/workflows/{session_id}/hypotheses/appliquer-propositions")
    return _rediriger(request, f"/sessions/{session_id}")


# Enregistrée avant la route dynamique /hypotheses/{hypothese_id}.
@app.post("/sessions/{session_id}/hypotheses/decider-lot")
def decider_hypotheses_lot(
    request: Request,
    session_id: int,
    statut: Annotated[str, Form()],
    hypothese_ids: Annotated[list[int] | None, Form()] = None,
) -> RedirectResponse:
    """R4 (H5) : applique la décision du PO (Confirmer OU Rejeter) au lot coché.

    Sans sélection, aucun appel api — simple retour à l'écran : jamais de
    décision implicite (A8).
    """
    if hypothese_ids:
        api_client.appeler(
            "POST",
            f"/workflows/{session_id}/hypotheses/decider-lot",
            json={"ids": hypothese_ids, "statut": statut},
        )
    return _rediriger(request, f"/sessions/{session_id}")


@app.post("/sessions/{session_id}/hypotheses/{hypothese_id}")
def decider_hypothese(
    request: Request, session_id: int, hypothese_id: int, statut: Annotated[str, Form()]
) -> RedirectResponse:
    api_client.appeler(
        "POST",
        f"/workflows/{session_id}/hypotheses/{hypothese_id}",
        json={"statut": statut},
    )
    return _rediriger(request, f"/sessions/{session_id}")


@app.post("/sessions/{session_id}/feedback")
def noter_story(
    request: Request,
    session_id: int,
    story_titre: Annotated[str, Form()],
    note: Annotated[int, Form()],
    commentaire: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """Note 1-5 + commentaire par story (E4.4) — alimente la télémétrie."""
    api_client.appeler(
        "POST",
        f"/workflows/{session_id}/feedback",
        json={"story_titre": story_titre, "note": note, "commentaire": commentaire},
    )
    return _rediriger(request, f"/sessions/{session_id}")


# R10 (UX9/H12) : « Suivi & réglages » — télémétrie + paramètres sur une page,
# chaque section dégradée indépendamment si son endpoint manque.
@app.get("/suivi", response_class=HTMLResponse)
def ecran_suivi(request: Request) -> HTMLResponse:
    statut_tele, telemetrie = api_client.appeler("GET", "/telemetrie")
    statut_tokens, tokens = api_client.appeler("GET", "/telemetrie/tokens")
    statut_parametres, parametres = api_client.appeler("GET", "/parametres")
    return templates.TemplateResponse(
        request=request,
        name="suivi.html",
        context={
            "telemetrie": telemetrie if statut_tele == 200 else None,
            "tokens": tokens if statut_tokens == 200 else None,
            "parametres": parametres if statut_parametres == 200 else None,
            "erreur": None,
        },
    )


@app.get("/parametres")
def ecran_parametres(request: Request) -> RedirectResponse:
    """R10 : l'ancienne route vit en redirection (liens/favoris préservés)."""
    return _rediriger(request, "/suivi#parametres")


@app.post("/parametres/modele")
def changer_modele(
    request: Request,
    modele: Annotated[str, Form()] = "",
    modele_libre: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """S3.12 : le champ libre (alias hors catalogue) prime sur le select."""
    choix = (modele_libre or modele).strip()
    if choix:
        api_client.appeler("PUT", "/parametres/modele-chat", json={"modele": choix})
    return _rediriger(request, "/suivi#parametres")


@app.post("/parametres/modele-defaut")
def modele_par_defaut(request: Request) -> RedirectResponse:
    api_client.appeler("DELETE", "/parametres/modele-chat")
    return _rediriger(request, "/suivi#parametres")


@app.get("/telemetrie")
def ecran_telemetrie(request: Request) -> RedirectResponse:
    """R10 : l'ancienne route vit en redirection (liens/favoris préservés)."""
    return _rediriger(request, "/suivi#telemetrie")


# --- Écran projets (E4.2, S2.9) ---


def _page_projets(request: Request, erreur: str | None = None) -> HTMLResponse:
    statut, projets = api_client.appeler("GET", "/projects")
    # R9 : le versant archivé, consultable et réversible depuis la même page.
    statut_archives, archives = api_client.appeler("GET", "/projects?archives=true")
    return templates.TemplateResponse(
        request=request,
        name="projets.html",
        context={
            "projets": projets if statut == 200 else [],
            "archives": archives if statut_archives == 200 and isinstance(archives, list) else [],
            "types_nfr": TYPES_NFR,
            "erreur": erreur or (None if statut == 200 else projets.get("detail")),
        },
    )


@app.get("/projets", response_class=HTMLResponse)
def ecran_projets(request: Request) -> HTMLResponse:
    return _page_projets(request)


@app.post("/projets", response_class=HTMLResponse, response_model=None)
def creer_projet(
    request: Request,
    nom: Annotated[str, Form()],
    contexte: Annotated[str, Form()] = "",
    nfr_type_1: Annotated[str, Form()] = "",
    nfr_formulation_1: Annotated[str, Form()] = "",
    nfr_valeur_1: Annotated[str, Form()] = "",
    nfr_type_2: Annotated[str, Form()] = "",
    nfr_formulation_2: Annotated[str, Form()] = "",
    nfr_valeur_2: Annotated[str, Form()] = "",
    nfr_type_3: Annotated[str, Form()] = "",
    nfr_formulation_3: Annotated[str, Form()] = "",
    nfr_valeur_3: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    nfrs = [
        {"type": type_nfr, "formulation": formulation.strip(), "valeur_cible": valeur or None}
        for type_nfr, formulation, valeur in [
            (nfr_type_1, nfr_formulation_1, nfr_valeur_1),
            (nfr_type_2, nfr_formulation_2, nfr_valeur_2),
            (nfr_type_3, nfr_formulation_3, nfr_valeur_3),
        ]
        if type_nfr and formulation.strip()
    ]
    corps = {"nom": nom, "contexte": contexte, "nfrs": nfrs, "dossiers": []}
    statut, projet = api_client.appeler("POST", "/projects", json=corps)
    if statut != 201:
        return _page_projets(request, erreur=projet.get("detail", "création impossible"))
    return _rediriger(request, f"/projets/{projet['id']}")


@app.get("/projets/{projet_id}", response_class=HTMLResponse)
def voir_projet(request: Request, projet_id: int) -> HTMLResponse:
    statut, projet = api_client.appeler("GET", f"/projects/{projet_id}")
    if statut != 200:
        return _page_erreur(request, statut, projet)
    statut_sugg, suggestions = api_client.appeler("GET", "/dossiers/suggestions")
    suggestions = suggestions if statut_sugg == 200 else []
    # Cases à cocher = union suggestions (S1.9) + dossiers déjà associés : un
    # ajout manuel (origine po) hors suggestions reste visible et décochable.
    associes = {d["dossier"] for d in projet["dossiers"]}
    suggeres = {s["dossier"] for s in suggestions}
    lignes = [
        {
            "dossier": s["dossier"],
            "nb_documents": s["nb_documents"],
            "coche": s["dossier"] in associes,
        }
        for s in suggestions
    ] + [
        {"dossier": d["dossier"], "nb_documents": None, "coche": True}
        for d in projet["dossiers"]
        if d["dossier"] not in suggeres
    ]
    return templates.TemplateResponse(
        request=request,
        name="projet.html",
        # R9 : types_nfr alimente le formulaire d'édition (NFR après création).
        context={"projet": projet, "dossiers": lignes, "types_nfr": TYPES_NFR},
    )


@app.post("/projets/{projet_id}/modifier", response_model=None)
async def modifier_projet(request: Request, projet_id: int) -> HTMLResponse | RedirectResponse:
    """R9 : édition du projet APRÈS création (nom, contexte, NFR) — PUT complet.

    Les dossiers A6 sont PRÉSERVÉS tels quels (leur formulaire dédié reste le
    seul à les toucher). Lignes NFR dynamiques : type + formulation remplis =
    NFR retenue ; formulation vidée = NFR retirée.
    """
    statut, projet = api_client.appeler("GET", f"/projects/{projet_id}")
    if statut != 200:
        return _page_erreur(request, statut, projet)
    formulaire = await request.form()
    nfrs = []
    index = 1
    while f"nfr_type_{index}" in formulaire or f"nfr_formulation_{index}" in formulaire:
        type_nfr = str(formulaire.get(f"nfr_type_{index}") or "").strip()
        formulation = str(formulaire.get(f"nfr_formulation_{index}") or "").strip()
        valeur = str(formulaire.get(f"nfr_valeur_{index}") or "").strip()
        if type_nfr and formulation:
            nfrs.append(
                {"type": type_nfr, "formulation": formulation, "valeur_cible": valeur or None}
            )
        index += 1
    corps = {
        "nom": str(formulaire.get("nom") or "").strip() or projet["nom"],
        "contexte": str(formulaire.get("contexte") or ""),
        "nfrs": nfrs,
        "dossiers": projet["dossiers"],
    }
    api_client.appeler("PUT", f"/projects/{projet_id}", json=corps)
    return _rediriger(request, f"/projets/{projet_id}")


@app.post("/projets/{projet_id}/gerer")
def gerer_projet_web(
    request: Request, projet_id: int, archiver: Annotated[str, Form()]
) -> RedirectResponse:
    """R9 (UX8) : archiver (masqué des listes et du choix de session) / désarchiver."""
    api_client.appeler("PATCH", f"/projects/{projet_id}", json={"archive": archiver == "1"})
    return _rediriger(request, "/projets")


@app.post("/projets/{projet_id}/supprimer")
def supprimer_projet_web(request: Request, projet_id: int) -> RedirectResponse:
    """R9 (H9, « suppression libre ») : définitif — les sessions liées continuent
    sans contexte projet (confirmé à l'écran)."""
    api_client.appeler("DELETE", f"/projects/{projet_id}")
    return _rediriger(request, "/projets")


@app.post("/projets/{projet_id}/dossiers", response_model=None)
def associer_dossiers(
    request: Request,
    projet_id: int,
    dossiers: Annotated[list[str] | None, Form()] = None,
    dossier_libre: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    """Association explicite projet ↔ dossiers (A6) : remplace la liste via PUT."""
    statut, projet = api_client.appeler("GET", f"/projects/{projet_id}")
    if statut != 200:
        return _page_erreur(request, statut, projet)
    _, suggestions = api_client.appeler("GET", "/dossiers/suggestions")
    suggeres = {s["dossier"] for s in suggestions} if isinstance(suggestions, list) else set()
    origines = {d["dossier"]: d["origine"] for d in projet["dossiers"]}
    ajout = [dossier_libre.strip()] if dossier_libre.strip() else []
    retenus = list(dict.fromkeys([*(dossiers or []), *ajout]))
    corps = {
        "nom": projet["nom"],
        "contexte": projet["contexte"],
        "nfrs": projet["nfrs"],
        "dossiers": [
            {"dossier": d, "origine": origines.get(d, "suggestion" if d in suggeres else "po")}
            for d in retenus
        ],
    }
    api_client.appeler("PUT", f"/projects/{projet_id}", json=corps)
    return _rediriger(request, f"/projets/{projet_id}")


# --- Écran « mes documents » (E4.3, S2.9, arbitrage A5) ---


# R8 : classes de badge DSFR par statut de parsing (état lisible d'un coup d'œil).
BADGES_STATUTS = {
    "parse": "fr-badge--success",
    "echec": "fr-badge--error",
    "ocr_requis": "fr-badge--warning",
    "a_parser": "fr-badge--info",
}


@app.get("/documents", response_class=HTMLResponse)
def ecran_documents(request: Request) -> HTMLResponse:
    statut, documents = api_client.appeler("GET", "/documents")
    if statut != 200:
        return _page_erreur(request, statut, documents)
    statut_stats, stats = api_client.appeler("GET", "/documents/stats")
    if statut_stats != 200:
        return _page_erreur(request, statut_stats, stats)
    # S3.10 : suivi des runs d'ingestion — l'écran reste servi sans l'endpoint.
    statut_runs, runs = api_client.appeler("GET", "/ingestion/runs")
    runs = runs if statut_runs == 200 and isinstance(runs, list) else []
    # S3.18 : dossiers existants pour la datalist du dépôt — dégradé en liste vide.
    statut_dossiers, dossiers = api_client.appeler("GET", "/documents/dossiers")
    dossiers = dossiers if statut_dossiers == 200 and isinstance(dossiers, list) else []
    # R8 : inventaire regroupé PAR DOSSIER (la clé d'association A6, S3.18),
    # avec les projets associés — dégradé sans l'endpoint projets.
    statut_projets, projets = api_client.appeler("GET", "/projects")
    projets_par_dossier: dict[str, list[str]] = {}
    if statut_projets == 200 and isinstance(projets, list):
        for projet in projets:
            for association in projet.get("dossiers", []):
                projets_par_dossier.setdefault(association["dossier"], []).append(projet["nom"])
    groupes: dict[str, list] = {}
    for document in documents:
        dossier = document["chemin"].split("/")[0] if "/" in document["chemin"] else "(racine)"
        groupes.setdefault(dossier, []).append(document)
    dossiers_groupes = [
        {"nom": nom, "documents": docs, "projets": projets_par_dossier.get(nom, [])}
        for nom, docs in sorted(groupes.items())
    ]
    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={
            "dossiers_groupes": dossiers_groupes,
            "nb_documents": len(documents),
            "stats": stats,
            "libelles": STATUTS_PARSING_LIBELLES,
            "badges_statuts": BADGES_STATUTS,
            "alerte_couverture": stats["couverture_parsing"] < SEUIL_COUVERTURE,
            "seuil": SEUIL_COUVERTURE,
            "runs": runs,
            "run_en_cours": any(r.get("statut") == "en_cours" for r in runs),
            "erreur_ingestion": request.query_params.get("erreur"),
            "dossiers": dossiers,
        },
    )


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def ecran_document(request: Request, document_id: int) -> HTMLResponse:
    """S3.14 : la fiche d'un document — tout ce que le pipeline en a fait."""
    statut, fiche = api_client.appeler("GET", f"/documents/{document_id}")
    if statut != 200:
        return _page_erreur(request, statut, fiche)
    return templates.TemplateResponse(
        request=request,
        name="document.html",
        context={"fiche": fiche, "libelles": STATUTS_PARSING_LIBELLES},
    )


@app.post("/documents/upload")
async def deposer_document(
    request: Request, fichier: UploadFile, dossier: Annotated[str, Form()]
) -> RedirectResponse:
    """S3.10/S3.18 : dépôt → un DOSSIER du corpus (celui qu'on associe à un projet)."""
    contenu = await fichier.read()
    statut, corps = api_client.envoyer_fichier(
        "/documents/upload",
        fichier.filename or "",
        contenu,
        fichier.content_type or "",
        donnees={"dossier": dossier},
    )
    if statut != 201:
        return _rediriger(request, f"/documents?erreur={corps.get('detail', 'dépôt refusé')}")
    return _rediriger(request, "/documents")


@app.post("/documents/indexer")
def lancer_indexation(request: Request) -> RedirectResponse:
    """S3.10 (arbitrage : manuel) : lance le pipeline complet en arrière-plan."""
    statut, corps = api_client.appeler("POST", "/ingestion/lancer")
    if statut not in (200, 202):
        return _rediriger(request, f"/documents?erreur={corps.get('detail', 'lancement refusé')}")
    return _rediriger(request, "/documents")


@app.post("/documents/runs/{run_id}/echec")
def debloquer_run(request: Request, run_id: int) -> RedirectResponse:
    api_client.appeler("POST", f"/ingestion/runs/{run_id}/echec")
    return _rediriger(request, "/documents")


@app.get("/documents/{document_id}/original")
def telecharger_original(document_id: int) -> Response:
    """S3.17 : proxy binaire de l'original (l'api n'est pas exposée au navigateur)."""
    statut, contenu, content_type, disposition = api_client.telecharger_binaire(
        f"/documents/{document_id}/original"
    )
    entetes = {"content-disposition": disposition} if disposition else {}
    return Response(
        content=contenu,
        status_code=statut if statut != 599 else 502,
        media_type=content_type,
        headers=entetes,
    )


@app.post("/documents/{document_id}/obsolete")
def basculer_obsolete(
    request: Request, document_id: int, est_obsolete: Annotated[str, Form()]
) -> RedirectResponse:
    """R8 (H10) : marquer obsolète (exclu des recherches) / réactiver — réversible."""
    api_client.appeler(
        "PATCH", f"/documents/{document_id}", json={"est_obsolete": est_obsolete == "1"}
    )
    return _rediriger(request, "/documents")


@app.post("/documents/{document_id}/supprimer")
def supprimer_document(request: Request, document_id: int) -> RedirectResponse:
    """S3.17 : suppression complète (base + fichiers) — confirmée côté écran."""
    statut, corps = api_client.appeler("DELETE", f"/documents/{document_id}")
    if statut not in (200, 204):
        return _rediriger(
            request, f"/documents?erreur={corps.get('detail', 'suppression refusée')}"
        )
    return _rediriger(request, "/documents")


@app.get("/sessions/{session_id}/export/{format_export}")
def exporter(session_id: int, format_export: str) -> PlainTextResponse:
    """Proxy des exports E5 (l'api n'est pas exposée au navigateur sur le lab)."""
    cible = "jira.csv" if format_export == "csv" else "markdown"
    statut, contenu, content_type = api_client.telecharger(
        f"/workflows/{session_id}/export/{cible}"
    )
    return PlainTextResponse(
        contenu, status_code=statut if statut != 599 else 502, media_type=content_type
    )
