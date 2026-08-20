from datetime import date, datetime

import pytest

from src.vamgar.connectors.base import TransactionConnector
from src.vamgar.schemas import Transaction, TransactionSource


class _FakeConnector(TransactionConnector):
    """نمونه آزمایشی برای اثبات قرارداد؛ جایگزین اتصال واقعی vendor نیست."""

    def fetch_transactions(self, merchant_id: str, since: date, until: date) -> list[Transaction]:
        return [
            Transaction(
                merchant_id=merchant_id,
                timestamp=datetime.combine(since, datetime.min.time()),
                amount=100_000,
                source=TransactionSource.POS,
            )
        ]


def test_cannot_instantiate_abstract_connector_directly():
    with pytest.raises(TypeError):
        TransactionConnector()


def test_concrete_connector_implements_contract():
    connector = _FakeConnector()

    transactions = connector.fetch_transactions("m1", date(2026, 1, 1), date(2026, 1, 31))

    assert len(transactions) == 1
    assert transactions[0].merchant_id == "m1"
