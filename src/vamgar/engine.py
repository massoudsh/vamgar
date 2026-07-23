"""Placeholder underwriting engine.

این ماژول فقط یک منطق ساده و placeholder دارد تا اسکلت API قابل اجرا باشد.
منطق واقعی (تحلیل cash gap، مدل ریسک مبتنی بر داده تراکنش واقعی) در فازهای
بعدی توسعه جایگزین این تابع می‌شود.
"""

from src.vamgar.schemas import CreditDecision, MerchantSalesSummary


def score_merchant(summary: MerchantSalesSummary) -> CreditDecision:
    """Compute a naive risk score and credit recommendation.

    Placeholder rule of thumb:
    - ریسک بالاتر با نوسان درآمد بیشتر و سابقه کوتاه‌تر افزایش می‌یابد.
    - سقف اعتبار پیشنهادی نسبتی از درآمد ماهانه است که با ریسک کاهش می‌یابد.
    - اگر نوسان درآمد بالا باشد، بازپرداخت درصدی از فروش پیشنهاد می‌شود.
    """
    history_factor = min(summary.months_of_history / 12, 1.0)
    risk_score = round(summary.revenue_volatility * (1 - 0.5 * history_factor), 4)

    safety_ratio = max(0.1, 1 - risk_score)
    recommended_credit_limit = round(summary.monthly_revenue_avg * safety_ratio, 2)

    repayment_model = "revenue_share" if summary.revenue_volatility > 0.4 else "fixed"

    return CreditDecision(
        merchant_id=summary.merchant_id,
        risk_score=risk_score,
        recommended_credit_limit=recommended_credit_limit,
        repayment_model=repayment_model,
    )
