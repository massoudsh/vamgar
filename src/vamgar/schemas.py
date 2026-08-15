"""Pydantic schemas for merchant credit scoring requests/responses."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransactionSource(str, Enum):
    """منبع داده تراکنش."""

    POS = "pos"
    PSP = "psp"
    MARKETPLACE = "marketplace"


class Transaction(BaseModel):
    """یک تراکنش نقدی خام مرچنت.

    amount مثبت یعنی ورود پول (فروش/تسویه) و amount منفی یعنی خروج پول
    (پرداخت به تأمین‌کننده، خرید موجودی و مانند آن).
    """

    merchant_id: str
    timestamp: datetime
    amount: float
    source: TransactionSource


class MerchantTransactionBatch(BaseModel):
    """دسته‌ای از تراکنش‌های خام یک مرچنت برای تحلیل."""

    merchant_id: str
    transactions: list[Transaction] = Field(..., min_length=1)


class CSVImportRequest(BaseModel):
    """ورودی import تراکنش خام از export دوره‌ای CSV یک منبع (کارت‌خوان/PSP/مارکت‌پلیس)."""

    merchant_id: str
    source: TransactionSource
    csv_text: str = Field(..., min_length=1, description="محتوای فایل CSV با هدر (ستون تاریخ + مبلغ)")


class CashGapEvent(BaseModel):
    """یک دوره پیوسته که موجودی نقدی تجمعی مرچنت منفی بوده (کسری نقدینگی)."""

    start_date: date
    end_date: date
    duration_days: int = Field(..., ge=1)
    max_deficit: float = Field(..., ge=0, description="بیشترین عمق کسری در این دوره (قدرمطلق، تومان)")


class CashGapAnalysis(BaseModel):
    """خروجی تحلیل cash gap بر پایه جریان نقدی روزانه واقعی مرچنت."""

    merchant_id: str
    period_start: date
    period_end: date
    gap_events: list[CashGapEvent]
    total_days_in_gap: int = Field(..., ge=0)
    max_gap_depth: float = Field(..., ge=0, description="بدترین (بیشترین) عمق کسری در کل بازه")
    avg_gap_depth: float = Field(..., ge=0, description="میانگین عمق کسری در دوره‌های گزارش‌شده")
    gap_frequency_per_month: float = Field(..., ge=0, description="تعداد دوره‌های کسری به ازای هر ماه")


class MerchantSalesSummary(BaseModel):
    """سیگنال تجمیع‌شده فروش مرچنت در یک بازه.

    این مدل می‌تواند دستی (برای فراخوان‌هایی که خودشان داده تجمیع‌شده
    دارند) یا به‌صورت خودکار از تراکنش‌های خام توسط
    ``vamgar.cashflow.build_sales_summary`` ساخته شود.
    """

    merchant_id: str
    monthly_revenue_avg: float = Field(..., ge=0, description="میانگین درآمد ماهانه (تومان)")
    revenue_volatility: float = Field(
        ..., ge=0, le=1, description="نوسان درآمد بین ۰ (پایدار) تا ۱ (بسیار ناپایدار)"
    )
    months_of_history: int = Field(..., ge=1, description="تعداد ماه‌هایی که داده تراکنش موجود است")


class CreditDecision(BaseModel):
    """Output of the credit scoring engine."""

    merchant_id: str
    risk_score: float = Field(..., ge=0, le=1, description="نمره ریسک؛ کمتر یعنی ریسک پایین‌تر")
    recommended_credit_limit: float = Field(..., ge=0, description="سقف اعتبار پیشنهادی (تومان)")
    repayment_model: str = Field(..., description="'fixed' یا 'revenue_share'")
