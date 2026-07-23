from src.vamgar.engine import score_merchant
from src.vamgar.schemas import MerchantSalesSummary


def test_low_volatility_gets_fixed_repayment():
    summary = MerchantSalesSummary(
        merchant_id="m1",
        monthly_revenue_avg=100_000_000,
        revenue_volatility=0.1,
        months_of_history=12,
    )
    decision = score_merchant(summary)

    assert decision.repayment_model == "fixed"
    assert 0 <= decision.risk_score <= 1
    assert decision.recommended_credit_limit <= summary.monthly_revenue_avg


def test_high_volatility_gets_revenue_share_repayment():
    summary = MerchantSalesSummary(
        merchant_id="m2",
        monthly_revenue_avg=50_000_000,
        revenue_volatility=0.8,
        months_of_history=2,
    )
    decision = score_merchant(summary)

    assert decision.repayment_model == "revenue_share"
    assert decision.recommended_credit_limit < summary.monthly_revenue_avg
