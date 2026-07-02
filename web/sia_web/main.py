"""Interface web du SIA PO — écran de conversation du workflow (E4.1, S2.8).

Front volontairement simple (CLAUDE.md) : formulaires HTML classiques, aucun
JavaScript requis — htmx pourra enrichir plus tard. Le DSFR est chargé par CDN
au MVP (à vendorer pour la prod, E7) avec des styles de repli locaux : la page
reste utilisable hors ligne. v1 assumée : les sources/avertissements du dernier
échange sont affichés dans la réponse du POST (non persistés côté UI) — au
rechargement, seul le fil (persisté par l'api) demeure.
"""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sia_web import api_client

app = FastAPI(title="SIA PO — Web")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

ETAPES_LIBELLES = {
    "recuperation_feature": "0 — Récupération de la Feature",
    "interview": "1 — Interview de refinement",
    "stories_candidates": "2 — Stories candidates",
    "redaction": "3 — Rédaction des stories",
    "controle_dor": "4 — Contrôle DoR",
    "synthese": "5 — Synthèse finale",
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _page_session(
    request: Request,
    session_id: int,
    dernier_resultat: dict | None = None,
    erreur: str | None = None,
) -> HTMLResponse:
    statut_etat, etat = api_client.appeler("GET", f"/workflows/{session_id}")
    if statut_etat != 200:
        return templates.TemplateResponse(
            request=request,
            name="erreur.html",
            context={"detail": etat.get("detail", "erreur inconnue")},
            status_code=statut_etat if statut_etat != 599 else 502,
        )
    _, messages = api_client.appeler("GET", f"/workflows/{session_id}/messages")
    return templates.TemplateResponse(
        request=request,
        name="session.html",
        context={
            "etat": etat,
            "messages": messages if isinstance(messages, list) else [],
            "libelle_etape": ETAPES_LIBELLES.get(etat["etape"], etat["etape"]),
            "dernier_resultat": dernier_resultat,
            "erreur": erreur,
        },
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    statut, projets = api_client.appeler("GET", "/projects")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "projets": projets if statut == 200 else [],
            "erreur": None if statut == 200 else projets.get("detail"),
        },
    )


@app.post("/sessions")
def creer_session(
    feature: Annotated[str, Form()], projet_id: Annotated[str, Form()] = ""
) -> RedirectResponse:
    corps = {"feature": feature, "projet_id": int(projet_id) if projet_id else None}
    statut, session = api_client.appeler("POST", "/workflows", json=corps)
    if statut != 201:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/sessions/{session['id']}", status_code=303)


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


@app.post("/sessions/{session_id}/valider")
def valider_etape(
    session_id: int,
    valide: Annotated[str, Form()],
    commentaire: Annotated[str, Form()] = "",
) -> RedirectResponse:
    api_client.appeler(
        "POST",
        f"/workflows/{session_id}/avancer",
        json={"valide": valide == "oui", "commentaire": commentaire},
    )
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


@app.post("/sessions/{session_id}/hypotheses/{hypothese_id}")
def decider_hypothese(
    session_id: int, hypothese_id: int, statut: Annotated[str, Form()]
) -> RedirectResponse:
    api_client.appeler(
        "POST",
        f"/workflows/{session_id}/hypotheses/{hypothese_id}",
        json={"statut": statut},
    )
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


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
