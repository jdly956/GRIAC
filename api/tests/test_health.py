from fastapi.testclient import TestClient

from sia_api.main import app

client = TestClient(app)


def test_health_repond_200() -> None:
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
