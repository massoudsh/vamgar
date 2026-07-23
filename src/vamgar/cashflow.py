"""تحلیل جریان نقدی واقعی مرچنت و تشخیص cash gap.

منطق این ماژول جایگزین فرمول placeholder قبلی می‌شود: به‌جای اینکه فراخوان
میانگین درآمد، نوسان و سابقه را دستی وارد کند، این مقادیر و همچنین دوره‌های
واقعی کسری نقدینگی از روی تراکنش‌های خام (کارت‌خوان/PSP/مارکت‌پلیس) محاسبه
می‌شوند.

الگوریتم:
1. تراکنش‌ها بر اساس روز جمع می‌شوند تا جریان نقدی خالص روزانه به دست بیاید.
2. تقویم بین اولین و آخرین روز پر می‌شود (روزهای بدون تراکنش = جریان صفر)
   تا مدت واقعی هر دوره کسری درست محاسبه شود.
3. موجودی تجمعی (running balance) از صفر شروع و روز به روز جمع می‌شود.
4. هر بازه پیوسته‌ای که موجودی تجمعی منفی است یک «cash gap» است؛ عمق آن
   بدترین (منفی‌ترین) موجودی در آن بازه و مدتش تعداد روزهای آن بازه است.
"""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, pstdev

from src.vamgar.schemas import CashGapAnalysis, CashGapEvent, MerchantSalesSummary, Transaction


def daily_net_cashflow(transactions: list[Transaction]) -> dict[date, float]:
    """جریان نقدی خالص روزانه (جمع تراکنش‌های همان روز)."""
    daily: dict[date, float] = defaultdict(float)
    for tx in transactions:
        daily[tx.timestamp.date()] += tx.amount
    return dict(daily)


def _fill_calendar(daily: dict[date, float]) -> list[tuple[date, float]]:
    """روزهای بین اولین و آخرین تراکنش را با جریان صفر پر می‌کند و بر اساس تاریخ مرتب برمی‌گرداند."""
    if not daily:
        return []
    start, end = min(daily), max(daily)
    filled = []
    current = start
    while current <= end:
        filled.append((current, daily.get(current, 0.0)))
        current += timedelta(days=1)
    return filled


def compute_running_balance(filled_daily: list[tuple[date, float]]) -> list[tuple[date, float]]:
    """موجودی تجمعی روز به روز، با شروع از صفر."""
    balance = 0.0
    result = []
    for day, net in filled_daily:
        balance += net
        result.append((day, balance))
    return result


def detect_cash_gaps(running_balance: list[tuple[date, float]]) -> list[CashGapEvent]:
    """دوره‌های پیوسته‌ای که موجودی تجمعی منفی است را به‌عنوان cash gap برمی‌گرداند."""
    events: list[CashGapEvent] = []
    gap_start: date | None = None
    worst_in_gap = 0.0

    def close_gap(end_day: date):
        events.append(
            CashGapEvent(
                start_date=gap_start,
                end_date=end_day,
                duration_days=(end_day - gap_start).days + 1,
                max_deficit=abs(worst_in_gap),
            )
        )

    for day, balance in running_balance:
        if balance < 0:
            if gap_start is None:
                gap_start = day
                worst_in_gap = balance
            else:
                worst_in_gap = min(worst_in_gap, balance)
        else:
            if gap_start is not None:
                close_gap(day - timedelta(days=1))
                gap_start = None

    if gap_start is not None:
        close_gap(running_balance[-1][0])

    return events


def analyze_cash_gaps(merchant_id: str, transactions: list[Transaction]) -> CashGapAnalysis:
    """پایپ‌لاین کامل: تراکنش خام -> تحلیل cash gap."""
    daily = daily_net_cashflow(transactions)
    filled = _fill_calendar(daily)
    running_balance = compute_running_balance(filled)
    gap_events = detect_cash_gaps(running_balance)

    period_start, period_end = filled[0][0], filled[-1][0]
    span_months = max((period_end - period_start).days / 30, 1 / 30)

    total_days_in_gap = sum(e.duration_days for e in gap_events)
    max_gap_depth = max((e.max_deficit for e in gap_events), default=0.0)
    avg_gap_depth = mean((e.max_deficit for e in gap_events)) if gap_events else 0.0
    gap_frequency_per_month = round(len(gap_events) / span_months, 4)

    return CashGapAnalysis(
        merchant_id=merchant_id,
        period_start=period_start,
        period_end=period_end,
        gap_events=gap_events,
        total_days_in_gap=total_days_in_gap,
        max_gap_depth=round(max_gap_depth, 2),
        avg_gap_depth=round(avg_gap_depth, 2),
        gap_frequency_per_month=gap_frequency_per_month,
    )


def build_sales_summary(merchant_id: str, transactions: list[Transaction]) -> MerchantSalesSummary:
    """میانگین درآمد ماهانه، نوسان درآمد و طول سابقه را از تراکنش‌های خام می‌سازد."""
    daily = daily_net_cashflow(transactions)
    dates = sorted(daily)
    period_start, period_end = dates[0], dates[-1]

    months_of_history = max(1, round((period_end - period_start).days / 30) or 1)

    monthly_inflow: dict[tuple[int, int], float] = defaultdict(float)
    for tx in transactions:
        if tx.amount > 0:
            key = (tx.timestamp.year, tx.timestamp.month)
            monthly_inflow[key] += tx.amount

    monthly_values = list(monthly_inflow.values()) or [0.0]
    monthly_revenue_avg = mean(monthly_values)

    if len(monthly_values) >= 2 and monthly_revenue_avg > 0:
        # نوسان درآمد ماه‌به‌ماه: ضریب تغییرات (انحراف معیار / میانگین)
        volatility = pstdev(monthly_values) / monthly_revenue_avg
    else:
        # با کمتر از دو ماه داده ماهانه، از نوسان روزانه به‌عنوان تخمین تقریبی
        # استفاده می‌شود (روزهای بدون فروش هم لحاظ می‌شوند تا بی‌ثباتی واقعی دیده شود).
        daily_inflows = [v for v in daily.values()]
        daily_mean = mean(daily_inflows) if daily_inflows else 0.0
        volatility = (pstdev(daily_inflows) / daily_mean / 3) if daily_mean > 0 else 1.0

    revenue_volatility = round(min(max(volatility, 0.0), 1.0), 4)

    return MerchantSalesSummary(
        merchant_id=merchant_id,
        monthly_revenue_avg=round(monthly_revenue_avg, 2),
        revenue_volatility=revenue_volatility,
        months_of_history=months_of_history,
    )
