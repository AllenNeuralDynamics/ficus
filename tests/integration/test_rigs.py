from fastapi.testclient import TestClient

from src.calibration_api.main import app


client = TestClient(app)


def test_get_rigs():
    response = client.get("/api/v1beta/rigs/")
    assert response.status_code == 200