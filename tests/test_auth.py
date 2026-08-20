from fastapi.testclient import TestClient

from src.vamgar.main import app

client = TestClient(app)

_SUMMARY = {"merchant_id": "m1", "monthly_revenue_avg": 10_000_000, "revenue_volatility": 0.2, "months_of_history": 6}


def test_open_by_default_when_no_api_keys_configured(monkeypatch):
    monkeypatch.delenv("VAMGAR_API_KEYS", raising=False)

    response = client.post("/score", json=_SUMMARY)

    assert response.status_code == 200


def test_rejects_missing_api_key_when_keys_configured(monkeypatch):
    monkeypatch.setenv("VAMGAR_API_KEYS", "secret-key-1,secret-key-2")

    response = client.post("/score", json=_SUMMARY)

    assert response.status_code == 401


def test_rejects_wrong_api_key(monkeypatch):
    monkeypatch.setenv("VAMGAR_API_KEYS", "secret-key-1")

    response = client.post("/score", json=_SUMMARY, headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401


def test_accepts_valid_api_key(monkeypatch):
    monkeypatch.setenv("VAMGAR_API_KEYS", "secret-key-1,secret-key-2")

    response = client.post("/score", json=_SUMMARY, headers={"X-API-Key": "secret-key-2"})

    assert response.status_code == 200


def test_health_never_requires_api_key(monkeypatch):
    monkeypatch.setenv("VAMGAR_API_KEYS", "secret-key-1")

    response = client.get("/health")

    assert response.status_code == 200
