from fastapi import FastAPI

app = FastAPI(title="SIA PO — API")


@app.get("/health")
def health() -> dict[str, str]:
    # Liveness sans dépendance DB : la readiness DB arrive avec les probes Helm (S1.6).
    return {"status": "ok"}
