from fastapi.testclient import TestClient

from src.vamgar.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_csv_endpoint_returns_credit_decision():
    payload = {
        "merchant_id": "m1",
        "source": "pos",
        "csv_text": (
            "date,amount\n"
            "2026-01-01T10:00:00,-1000000\n"
            "2026-01-02T10:00:00,200000\n"
            "2026-01-03T10:00:00,200000\n"
            "2026-01-04T10:00:00,800000\n"
        ),
    }

    response = client.post("/score/csv", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["merchant_id"] == "m1"
    assert 0 <= body["risk_score"] <= 1
    assert body["recommended_credit_limit"] >= 0


def test_score_csv_endpoint_returns_400_on_malformed_csv():
    payload = {"merchant_id": "m1", "source": "pos", "csv_text": "date,total\n2026-01-01,1000\n"}

    response = client.post("/score/csv", json=payload)

    assert response.status_code == 400
