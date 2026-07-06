"""Interface web du SIA PO — conversation (E4.1, S2.8), écrans projets et
« mes documents » (E4.2/E4.3, S2.9).

Front volontairement simple (CLAUDE.md) : formulaires HTML classiques, aucun
JavaScript requis — htmx pourra enrichir plus tard. Le DSFR est chargé par CDN
au MVP (à vendorer pour la prod, E7) avec des styles de repli locaux : la page
reste utilisable hors ligne. v1 assumée : les sources/avertissements du dernier
échange sont affichés dans la réponse du POST (non persistés côté UI) — au
rechargement, seul le fil (persisté par l'api) demeure.

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

from fastapi import FastAPI, Form, Request
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
    context_processors=[_contexte_racine],
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


def _page_session(
    request: Request,
    session_id: int,
    dernier_resultat: dict | None = None,
    erreur: str | None = None,
) -> HTMLResponse:
    statut_etat, etat = api_client.appeler("GET", f"/workflows/{session_id}")
    if statut_etat != 200:
        return _page_erreur(request, statut_etat, etat)
    _, messages = api_client.appeler("GET", f"/workflows/{session_id}/messages")
    _, stories = api_client.appeler("GET", f"/workflows/{session_id}/stories")
    statut_conso, conso = api_client.appeler("GET", f"/workflows/{session_id}/conso")
    statut_parametres, parametres = api_client.appeler("GET", "/parametres")
    # S3.7 : le registre replié ne se déplie tout seul que si une levée
    # proposée (S2.13) attend la décision du PO.
    nb_levees_a_decider = sum(
        1
        for h in etat.get("hypotheses", [])
        if h.get("statut") == "en_attente" and h.get("statut_propose")
    )
    return templates.TemplateResponse(
        request=request,
        name="session.html",
        context={
            "etat": etat,
            "messages": messages if isinstance(messages, list) else [],
            "stories": stories if isinstance(stories, list) else [],
            "libelle_etape": ETAPES_LIBELLES.get(etat["etape"], etat["etape"]),
            "dernier_resultat": dernier_resultat,
            "nb_levees_a_decider": nb_levees_a_decider,
            # S3.11 : conso de la session (None si l'api ne répond pas — simple
            # indication, jamais bloquant).
            "conso": conso if statut_conso == 200 else None,
            # S3.12 : le PO sait quel modèle écrit.
            "modele_actif": parametres.get("modele_actif") if statut_parametres == 200 else None,
            "erreur": erreur,
        },
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    statut, projets = api_client.appeler("GET", "/projects")
    statut_sessions, sessions = api_client.appeler("GET", "/workflows")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "projets": projets if statut == 200 else [],
            "sessions": sessions if statut_sessions == 200 else [],
            "libelles_etapes": ETAPES_LIBELLES,
            "erreur": None if statut == 200 else projets.get("detail"),
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
        return _page_session(request, session_id, erreur=resultat.get("detail"))
    message = (
        "Étape validée (Oui) — poursuis le workflow sur l'étape courante."
        if valide == "oui"
        else f"Étape non validée (Non) — itère sur cette étape en tenant compte de : {commentaire}"
    )
    statut_moteur, reponse_moteur = api_client.appeler(
        "POST", f"/workflows/{session_id}/message", json={"message": message}
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
    statut, resultat = api_client.appeler(
        "POST",
        f"/workflows/{session_id}/message",
        json={
            "message": "Story validée — enchaîne sur la STORY SUIVANTE de la liste des "
            "candidates (rédaction complète puis contrôle DoR), sans changer d'étape. "
            "S'il ne reste aucune story à rédiger, dis-le explicitement."
        },
    )
    if statut != 200:
        return _page_session(request, session_id, erreur=resultat.get("detail"))
    return _page_session(request, session_id, dernier_resultat=resultat)


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


@app.get("/parametres", response_class=HTMLResponse)
def ecran_parametres(request: Request, erreur: str | None = None) -> HTMLResponse:
    statut, parametres = api_client.appeler("GET", "/parametres")
    if statut != 200:
        return _page_erreur(request, statut, parametres)
    return templates.TemplateResponse(
        request=request,
        name="parametres.html",
        context={"parametres": parametres, "erreur": erreur},
    )


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
    return _rediriger(request, "/parametres")


@app.post("/parametres/modele-defaut")
def modele_par_defaut(request: Request) -> RedirectResponse:
    api_client.appeler("DELETE", "/parametres/modele-chat")
    return _rediriger(request, "/parametres")


@app.get("/telemetrie", response_class=HTMLResponse)
def ecran_telemetrie(request: Request) -> HTMLResponse:
    statut, telemetrie = api_client.appeler("GET", "/telemetrie")
    statut_tokens, tokens = api_client.appeler("GET", "/telemetrie/tokens")
    if statut != 200:
        return _page_erreur(request, statut, telemetrie)
    return templates.TemplateResponse(
        request=request,
        name="telemetrie.html",
        context={
            "telemetrie": telemetrie,
            # S3.11 : la jauge tokens est une indication — l'écran reste servi
            # même si l'endpoint conso est indisponible.
            "tokens": tokens if statut_tokens == 200 else None,
        },
    )


# --- Écran projets (E4.2, S2.9) ---


def _page_projets(request: Request, erreur: str | None = None) -> HTMLResponse:
    statut, projets = api_client.appeler("GET", "/projects")
    return templates.TemplateResponse(
        request=request,
        name="projets.html",
        context={
            "projets": projets if statut == 200 else [],
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
        context={"projet": projet, "dossiers": lignes},
    )


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


@app.get("/documents", response_class=HTMLResponse)
def ecran_documents(request: Request) -> HTMLResponse:
    statut, documents = api_client.appeler("GET", "/documents")
    if statut != 200:
        return _page_erreur(request, statut, documents)
    statut_stats, stats = api_client.appeler("GET", "/documents/stats")
    if statut_stats != 200:
        return _page_erreur(request, statut_stats, stats)
    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={
            "documents": documents,
            "stats": stats,
            "libelles": STATUTS_PARSING_LIBELLES,
            "alerte_couverture": stats["couverture_parsing"] < SEUIL_COUVERTURE,
            "seuil": SEUIL_COUVERTURE,
        },
    )


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
