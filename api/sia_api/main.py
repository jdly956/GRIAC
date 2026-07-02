"""Point d'entrée de l'API SIA PO (S1.2, config S1.4, projets S1.11).

Périmètre actuel : /health (healthcheck compose puis probes Kubernetes S1.6)
et le CRUD projets/NFR (S1.11). Les routes métier RAG/génération/feedback/
export arrivent avec les epics E2-E5.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sia_api.config import charger_settings
from sia_api.projets import router as router_projets


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    # Échec au démarrage si la config Albert est absente ou incomplète (S1.4) :
    # mieux vaut refuser de démarrer avec un message explicite que de découvrir
    # l'absence de clé au premier appel Albert.
    application.state.settings = charger_settings()
    yield


app = FastAPI(title="SIA PO — API", lifespan=lifespan)
app.include_router(router_projets)


@app.get("/health")
def health() -> dict[str, str]:
    # Liveness volontairement sans dépendance DB : un incident PostgreSQL ne doit
    # pas faire redémarrer l'API en cascade. La readiness DB arrive avec S1.6.
    return {"status": "ok"}
