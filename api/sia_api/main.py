"""Point d'entrée de l'API SIA PO (S1.2).

Périmètre actuel : le seul endpoint /health, consommé par le healthcheck du
compose (infra/compose.yaml) puis par les probes Kubernetes (S1.6). Les routes
métier (RAG, génération, feedback, export) arrivent avec les epics E2-E5.
"""

from fastapi import FastAPI

app = FastAPI(title="SIA PO — API")


@app.get("/health")
def health() -> dict[str, str]:
    # Liveness volontairement sans dépendance DB : un incident PostgreSQL ne doit
    # pas faire redémarrer l'API en cascade. La readiness DB arrive avec S1.6.
    return {"status": "ok"}
