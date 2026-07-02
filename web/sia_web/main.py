"""Interface web du SIA PO (S1.2).

Périmètre actuel : page placeholder servie en Jinja2 (avec le bandeau D15
« Ne collez pas de données personnelles », contrainte CLAUDE.md) et /health
pour le healthcheck compose puis les probes Kubernetes. L'interface réelle
(DSFR + htmx : conversation du workflow, panneau sources, écrans projet et
documents) arrive avec l'epic E4 — FastAPI+Jinja2 est déjà le bon runtime.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="SIA PO — Web")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")
