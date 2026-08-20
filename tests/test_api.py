import io
from datetime import datetime

from fastapi.testclient import TestClient
from openpyxl import Workbook

from src.vamgar.main import app

client = TestClient(app)


def _xlsx_bytes(header: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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


def test_score_xlsx_endpoint_returns_credit_decision():
    content = _xlsx_bytes(
        ["date", "amount"],
        [
            [datetime(2026, 1, 1, 10, 0, 0), -1_000_000],
            [datetime(2026, 1, 2, 10, 0, 0), 200_000],
            [datetime(2026, 1, 3, 10, 0, 0), 200_000],
            [datetime(2026, 1, 4, 10, 0, 0), 800_000],
        ],
    )

    response = client.post(
        "/score/xlsx",
        data={"merchant_id": "m1", "source": "pos"},
        files={"file": ("statement.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["merchant_id"] == "m1"
    assert 0 <= body["risk_score"] <= 1


def test_score_xlsx_endpoint_returns_400_on_malformed_file():
    content = _xlsx_bytes(["date", "total"], [[datetime(2026, 1, 1), 1000]])

    response = client.post(
        "/score/xlsx",
        data={"merchant_id": "m1", "source": "pos"},
        files={"file": ("statement.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 400


def test_merchant_history_returns_past_decisions_newest_first():
    payload = {"merchant_id": "m1", "monthly_revenue_avg": 10_000_000, "revenue_volatility": 0.1, "months_of_history": 6}
    client.post("/score", json=payload)
    client.post("/score", json=payload)

    response = client.get("/merchants/m1/history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["merchant_id"] == "m1"


def test_merchant_history_empty_for_unknown_merchant():
    response = client.get("/merchants/unknown-merchant/history")

    assert response.status_code == 200
    assert response.json() == []
