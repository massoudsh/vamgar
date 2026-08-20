from datetime import datetime

from src.vamgar import storage
from src.vamgar.schemas import CreditDecision, Transaction, TransactionSource


def _tx(day: str, amount: float) -> Transaction:
    return Transaction(
        merchant_id="m1", timestamp=datetime.fromisoformat(day), amount=amount, source=TransactionSource.POS
    )


def test_save_transactions_is_idempotent():
    transactions = [_tx("2026-01-01T10:00:00", 1000), _tx("2026-01-02T10:00:00", 2000)]

    first = storage.save_transactions(transactions)
    second = storage.save_transactions(transactions)  # همان داده دوباره import می‌شود

    assert first == 2
    assert second == 0  # هیچ رکورد جدیدی اضافه نشد


def test_decision_history_returns_newest_first():
    older = CreditDecision(merchant_id="m1", risk_score=0.2, recommended_credit_limit=1000, repayment_model="fixed")
    newer = CreditDecision(
        merchant_id="m1", risk_score=0.5, recommended_credit_limit=500, repayment_model="revenue_share"
    )

    storage.save_decision(older)
    storage.save_decision(newer)

    history = storage.get_decision_history("m1")

    assert len(history) == 2
    assert history[0]["repayment_model"] == "revenue_share"
    assert history[1]["repayment_model"] == "fixed"


def test_decision_history_scoped_to_merchant():
    storage.save_decision(
        CreditDecision(merchant_id="m1", risk_score=0.1, recommended_credit_limit=100, repayment_model="fixed")
    )
    storage.save_decision(
        CreditDecision(merchant_id="m2", risk_score=0.1, recommended_credit_limit=100, repayment_model="fixed")
    )

    assert len(storage.get_decision_history("m1")) == 1
    assert len(storage.get_decision_history("m2")) == 1
    assert storage.get_decision_history("m3") == []
