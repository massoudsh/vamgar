"""Vamgar API and dashboard."""

import hashlib
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src.vamgar import storage
from src.vamgar.auth import require_api_key
from src.vamgar.cashflow import analyze_cash_gaps
from src.vamgar.engine import score_merchant, score_merchant_from_transactions
from src.vamgar.importers import (
    CSVImportError,
    XLSXImportError,
    parse_csv_transactions,
    parse_xlsx_transactions,
)
from src.vamgar.schemas import (
    CashGapAnalysis,
    CreditDecision,
    CreditDecisionRecord,
    CSVImportRequest,
    MerchantSalesSummary,
    MerchantTransactionBatch,
    TransactionSource,
)

app = FastAPI(title="Vamgar", description="AI Merchant Credit & Working Capital Engine")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/score", response_model=CreditDecision, dependencies=[Depends(require_api_key)])
def score(summary: MerchantSalesSummary) -> CreditDecision:
    """امتیازدهی از روی خلاصه فروش از‌قبل‌تجمیع‌شده (بدون تحلیل cash gap)."""
    decision = score_merchant(summary)
    storage.save_decision(
        decision,
        source_endpoint="/score",
        input_payload=summary.model_dump(mode="json"),
    )
    return decision


@app.post(
    "/score/transactions", response_model=CreditDecision, dependencies=[Depends(require_api_key)]
)
def score_from_transactions(batch: MerchantTransactionBatch) -> CreditDecision:
    """امتیازدهی کامل از روی تراکنش‌های خام (کارت‌خوان/PSP/مارکت‌پلیس)."""
    storage.save_transactions(batch.transactions)
    decision = score_merchant_from_transactions(batch.merchant_id, batch.transactions)
    storage.save_decision(
        decision,
        source_endpoint="/score/transactions",
        input_payload={
            "merchant_id": batch.merchant_id,
            "transaction_count": len(batch.transactions),
            "amount_sum": round(sum(tx.amount for tx in batch.transactions), 2),
        },
    )
    return decision


@app.post("/cashflow/analyze", response_model=CashGapAnalysis, dependencies=[Depends(require_api_key)])
def cashflow_analyze(batch: MerchantTransactionBatch) -> CashGapAnalysis:
    """فقط تحلیل cash gap را برمی‌گرداند (برای بازبینی/دیباگ)."""
    storage.save_transactions(batch.transactions)
    return analyze_cash_gaps(batch.merchant_id, batch.transactions)


@app.post("/score/csv", response_model=CreditDecision, dependencies=[Depends(require_api_key)])
def score_from_csv(payload: CSVImportRequest) -> CreditDecision:
    """امتیازدهی کامل از روی export دوره‌ای CSV یک منبع (کارت‌خوان/PSP/مارکت‌پلیس)."""
    try:
        transactions = parse_csv_transactions(payload.csv_text, payload.merchant_id, payload.source)
    except CSVImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage.save_transactions(transactions)
    decision = score_merchant_from_transactions(payload.merchant_id, transactions)
    storage.save_decision(
        decision,
        source_endpoint="/score/csv",
        input_payload={
            "merchant_id": payload.merchant_id,
            "source": payload.source.value,
            "csv_sha256": storage.hash_input(payload.csv_text),
            "transaction_count": len(transactions),
        },
    )
    return decision


@app.post("/score/xlsx", response_model=CreditDecision, dependencies=[Depends(require_api_key)])
async def score_from_xlsx(
    merchant_id: str = Form(...),
    source: TransactionSource = Form(...),
    file: UploadFile = File(...),
) -> CreditDecision:
    """امتیازدهی کامل از روی export دوره‌ای xlsx یک منبع (کارت‌خوان/PSP/مارکت‌پلیس)."""
    content = await file.read()
    try:
        transactions = parse_xlsx_transactions(content, merchant_id, source)
    except XLSXImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage.save_transactions(transactions)
    decision = score_merchant_from_transactions(merchant_id, transactions)
    storage.save_decision(
        decision,
        source_endpoint="/score/xlsx",
        input_payload={
            "merchant_id": merchant_id,
            "source": source.value,
            "file_sha256": hashlib.sha256(content).hexdigest(),
            "transaction_count": len(transactions),
        },
    )
    return decision


@app.get(
    "/merchants/{merchant_id}/history",
    response_model=list[CreditDecisionRecord],
    dependencies=[Depends(require_api_key)],
)
def merchant_history(merchant_id: str, limit: int = 50) -> list[dict]:
    """تاریخچه تصمیم‌های اعتباری ثبت‌شده یک مرچنت (جدیدترین اول)."""
    return storage.get_decision_history(merchant_id, limit)


app.mount("/app", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend", html=True), name="dashboard")
