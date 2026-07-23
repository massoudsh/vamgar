"""Pydantic schemas for merchant credit scoring requests/responses."""

from pydantic import BaseModel, Field


class MerchantSalesSummary(BaseModel):
    """Aggregated sales signal for a merchant over a lookback period.

    This is a simplified placeholder input. In a real implementation this
    would be derived from raw POS/PSP/marketplace transaction data.
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
