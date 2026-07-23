from datetime import datetime

from src.vamgar.cashflow import analyze_cash_gaps, build_sales_summary
from src.vamgar.engine import score_merchant_from_transactions
from src.vamgar.schemas import Transaction, TransactionSource


def _tx(day: str, amount: float, source: TransactionSource = TransactionSource.POS) -> Transaction:
    return Transaction(
        merchant_id="m1",
        timestamp=datetime.fromisoformat(day),
        amount=amount,
        source=source,
    )


def test_detects_a_single_cash_gap_period():
    # روز ۱: خرید موجودی (خروج بزرگ) -> موجودی منفی می‌شود
    # روزهای ۲ و ۳: فروش تدریجی -> موجودی هنوز منفی
    # روز ۴: فروش کافی -> موجودی مثبت می‌شود (گپ بسته می‌شود)
    transactions = [
        _tx("2026-01-01T10:00:00", -1_000_000, TransactionSource.MARKETPLACE),
        _tx("2026-01-02T10:00:00", 200_000),
        _tx("2026-01-03T10:00:00", 200_000),
        _tx("2026-01-04T10:00:00", 800_000),
    ]

    analysis = analyze_cash_gaps("m1", transactions)

    assert len(analysis.gap_events) == 1
    gap = analysis.gap_events[0]
    assert gap.duration_days == 3  # روزهای ۱ تا ۳
    assert gap.max_deficit == 1_000_000  # بدترین موجودی درست بعد از خرید موجودی
    assert analysis.total_days_in_gap == 3
    assert analysis.max_gap_depth == 1_000_000


def test_no_gap_when_balance_never_goes_negative():
    transactions = [
        _tx("2026-01-01T10:00:00", 500_000, TransactionSource.PSP),
        _tx("2026-01-02T10:00:00", 300_000, TransactionSource.PSP),
    ]

    analysis = analyze_cash_gaps("m1", transactions)

    assert analysis.gap_events == []
    assert analysis.total_days_in_gap == 0
    assert analysis.max_gap_depth == 0


def test_build_sales_summary_computes_monthly_average_from_real_inflows():
    transactions = [
        _tx("2026-01-05T09:00:00", 10_000_000),
        _tx("2026-01-20T09:00:00", 10_000_000),
        _tx("2026-02-05T09:00:00", 30_000_000),
    ]

    summary = build_sales_summary("m1", transactions)

    # میانگین دو ماه: (20M + 30M) / 2 = 25M
    assert summary.monthly_revenue_avg == 25_000_000
    assert summary.months_of_history >= 1
    assert 0 <= summary.revenue_volatility <= 1


def test_frequent_deep_gaps_push_toward_revenue_share_repayment():
    # دو چرخه‌ی پشت‌سرهم خرید موجودی/فروش در یک بازه کوتاه -> cash gap مکرر و عمیق
    transactions = [
        _tx("2026-01-01T09:00:00", -5_000_000, TransactionSource.MARKETPLACE),
        _tx("2026-01-03T09:00:00", 6_000_000),
        _tx("2026-01-10T09:00:00", -5_000_000, TransactionSource.MARKETPLACE),
        _tx("2026-01-12T09:00:00", 6_000_000),
    ]

    decision = score_merchant_from_transactions("m1", transactions)

    assert decision.repayment_model == "revenue_share"
    assert decision.recommended_credit_limit > 0
