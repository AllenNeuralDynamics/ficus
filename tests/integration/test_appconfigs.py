from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_get_rigs():
    response = client.get("/api/v1/appconfigs/")
    assert response.status_code == 200
