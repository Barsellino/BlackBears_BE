from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "OK"

def test_create_session():
    response = client.post("/session")
    assert response.status_code == 200
    assert "session_id" in response.json()
    assert len(response.json()["session_id"]) == 4