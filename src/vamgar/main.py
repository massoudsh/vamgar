"""Vamgar API skeleton."""

from fastapi import FastAPI

from src.vamgar.engine import score_merchant
from src.vamgar.schemas import CreditDecision, MerchantSalesSummary

app = FastAPI(title="Vamgar", description="AI Merchant Credit & Working Capital Engine")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/score", response_model=CreditDecision)
def score(summary: MerchantSalesSummary) -> CreditDecision:
    return score_merchant(summary)
