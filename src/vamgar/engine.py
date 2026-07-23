"""موتور تصمیم‌گیری اعتباری Vamgar.

ریسک و سقف اعتبار پیشنهادی نه‌فقط از نوسان درآمد، بلکه از عمق و فراوانی
واقعیِ دوره‌های کسری نقدینگی (cash gap) که در ``vamgar.cashflow`` از روی
تراکنش‌های خام محاسبه شده‌اند به دست می‌آید. اگر تحلیل cash gap در دسترس
نباشد (مثلاً فراخوانی که فقط خلاصه فروش را می‌فرستد)، موتور تنها بر پایه
نوسان درآمد و طول سابقه تصمیم می‌گیرد.
"""

from src.vamgar.cashflow import analyze_cash_gaps, build_sales_summary
from src.vamgar.schemas import CashGapAnalysis, CreditDecision, MerchantSalesSummary, Transaction

# اگر بیش از این تعداد دوره کسری در ماه رخ دهد، جریمه فراوانی به سقف می‌رسد.
MAX_GAP_FREQUENCY_FOR_FULL_PENALTY = 4.0
# از این تعداد دوره کسری در ماه به بالا، بازپرداخت درصدی از فروش پیشنهاد می‌شود.
FREQUENT_GAP_THRESHOLD_PER_MONTH = 2.0


def score_merchant(
    summary: MerchantSalesSummary, gap_analysis: CashGapAnalysis | None = None
) -> CreditDecision:
    """ریسک، سقف اعتبار و مدل بازپرداخت را محاسبه می‌کند.

    - نوسان درآمد و طول سابقه، ریسک پایه را می‌سازند (سابقه بیشتر = ریسک کمتر).
    - اگر تحلیل cash gap موجود باشد، عمق کسری (نسبت به درآمد ماهانه) و
      فراوانی وقوع آن هم در ریسک نهایی وزن می‌گیرند.
    - سقف اعتبار پیشنهادی طوری تنظیم می‌شود که حداقل عمق متوسط cash gap
      واقعی مرچنت را پوشش دهد (تا مشکل واقعی را حل کند)، اما هرگز از
      درآمد ماهانه فراتر نرود.
    - نوسان بالا یا cash gap مکرر یعنی بازپرداخت ثابت مناسب نیست؛ در این
      حالت بازپرداخت درصدی از فروش روزانه پیشنهاد می‌شود.
    """
    history_factor = min(summary.months_of_history / 12, 1.0)
    volatility_risk = summary.revenue_volatility * (1 - 0.5 * history_factor)

    has_gaps = gap_analysis is not None and gap_analysis.gap_events
    if has_gaps:
        gap_depth_ratio = min(gap_analysis.avg_gap_depth / max(summary.monthly_revenue_avg, 1), 1.0)
        gap_frequency_ratio = min(
            gap_analysis.gap_frequency_per_month / MAX_GAP_FREQUENCY_FOR_FULL_PENALTY, 1.0
        )
        gap_risk = 0.5 * gap_depth_ratio + 0.5 * gap_frequency_ratio
        risk_score = round(min(1.0, 0.6 * volatility_risk + 0.4 * gap_risk), 4)
    else:
        risk_score = round(volatility_risk, 4)

    safety_ratio = max(0.1, 1 - risk_score)
    safety_based_limit = summary.monthly_revenue_avg * safety_ratio

    if has_gaps:
        # اعتبار باید حداقل عمق متوسط cash gap واقعی را با حاشیه امن پوشش دهد،
        # اما از درآمد ماهانه و از سقف امنِ محاسبه‌شده بیشتر نشود مگر لازم باشد.
        gap_coverage_need = gap_analysis.avg_gap_depth * 1.2
        recommended_credit_limit = min(
            max(safety_based_limit, gap_coverage_need), summary.monthly_revenue_avg
        )
    else:
        recommended_credit_limit = safety_based_limit

    frequent_gaps = has_gaps and gap_analysis.gap_frequency_per_month >= FREQUENT_GAP_THRESHOLD_PER_MONTH
    repayment_model = (
        "revenue_share" if (summary.revenue_volatility > 0.4 or frequent_gaps) else "fixed"
    )

    return CreditDecision(
        merchant_id=summary.merchant_id,
        risk_score=risk_score,
        recommended_credit_limit=round(recommended_credit_limit, 2),
        repayment_model=repayment_model,
    )


def score_merchant_from_transactions(merchant_id: str, transactions: list[Transaction]) -> CreditDecision:
    """پایپ‌لاین کامل: تراکنش خام مرچنت -> تحلیل cash gap + خلاصه فروش -> تصمیم اعتباری."""
    summary = build_sales_summary(merchant_id, transactions)
    gap_analysis = analyze_cash_gaps(merchant_id, transactions)
    return score_merchant(summary, gap_analysis)
