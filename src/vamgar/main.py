"""Vamgar API."""

from fastapi import FastAPI, HTTPException

from src.vamgar.cashflow import analyze_cash_gaps
from src.vamgar.engine import score_merchant, score_merchant_from_transactions
from src.vamgar.importers import CSVImportError, parse_csv_transactions
from src.vamgar.schemas import (
    CashGapAnalysis,
    CreditDecision,
    CSVImportRequest,
    MerchantSalesSummary,
    MerchantTransactionBatch,
)

app = FastAPI(title="Vamgar", description="AI Merchant Credit & Working Capital Engine")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/score", response_model=CreditDecision)
def score(summary: MerchantSalesSummary) -> CreditDecision:
    """امتیازدهی از روی خلاصه فروش از‌قبل‌تجمیع‌شده (بدون تحلیل cash gap)."""
    return score_merchant(summary)


@app.post("/score/transactions", response_model=CreditDecision)
def score_from_transactions(batch: MerchantTransactionBatch) -> CreditDecision:
    """امتیازدهی کامل از روی تراکنش‌های خام (کارت‌خوان/PSP/مارکت‌پلیس)."""
    return score_merchant_from_transactions(batch.merchant_id, batch.transactions)


@app.post("/cashflow/analyze", response_model=CashGapAnalysis)
def cashflow_analyze(batch: MerchantTransactionBatch) -> CashGapAnalysis:
    """فقط تحلیل cash gap را برمی‌گرداند (برای بازبینی/دیباگ)."""
    return analyze_cash_gaps(batch.merchant_id, batch.transactions)


@app.post("/score/csv", response_model=CreditDecision)
def score_from_csv(payload: CSVImportRequest) -> CreditDecision:
    """امتیازدهی کامل از روی export دوره‌ای CSV یک منبع (کارت‌خوان/PSP/مارکت‌پلیس)."""
    try:
        transactions = parse_csv_transactions(payload.csv_text, payload.merchant_id, payload.source)
    except CSVImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return score_merchant_from_transactions(payload.merchant_id, transactions)
