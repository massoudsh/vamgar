"""Provider-neutral aggregation over the existing credit decision pipeline."""

from dataclasses import dataclass

from src.vamgar.cashflow import analyze_cash_gaps
from src.vamgar.engine import score_merchant_from_transactions
from src.vamgar.schemas import CreditDecision, ProviderOffer, Transaction


@dataclass(frozen=True)
class ProviderProfile:
    provider_id: str
    name: str
    max_risk_score: float
    credit_multiplier: float
    repayment_models: tuple[str, ...]
    policy_version: str
    estimated_fee_rate: float
    decision_sla_hours: int
    data_requirements: tuple[str, ...]


PROVIDER_PROFILES = (
    ProviderProfile("digipay", "دیجی‌پی", 0.65, 0.8, ("fixed", "revenue_share"), "2026.1", 0.04, 24, ("تراکنش POS", "شناسه مرچنت")),
    ProviderProfile("azki-vam", "ازکی‌وام", 0.55, 0.7, ("fixed",), "2026.1", 0.05, 48, ("تراکنش POS", "سابقه تصمیم")),
    ProviderProfile("snapp-pay", "اسنپ‌پی", 0.7, 0.75, ("fixed", "revenue_share"), "2026.1", 0.035, 24, ("تراکنش فروش", "شناسه مرچنت")),
    ProviderProfile("basalam-credit", "اعتبار فروشندگان باسلام", 0.6, 0.65, ("revenue_share",), "2026.1", 0.03, 12, ("سابقه سفارش", "تراکنش تسویه")),
    ProviderProfile("lendme", "لندمی", 0.5, 0.6, ("fixed",), "2026.1", 0.06, 72, ("تراکنش بانکی", "احراز هویت")),
    ProviderProfile("other-lendtech", "سایر ارائه‌دهندگان لندتک", 0.75, 0.5, ("fixed", "revenue_share"), "2026.1", 0.07, 72, ("داده تراکنش",)),
)


def _reason(profile: ProviderProfile, decision: CreditDecision) -> str:
    if decision.risk_score > profile.max_risk_score:
        return "نمره ریسک مرچنت از آستانه این ارائه‌دهنده بالاتر است."
    if decision.repayment_model not in profile.repayment_models:
        return "مدل بازپرداخت پیشنهادی با محصولات فعلی این ارائه‌دهنده هم‌خوان نیست."
    return "با نمره ریسک و مدل بازپرداخت مرچنت سازگار است."


def aggregate_offers(merchant_id: str, transactions: list[Transaction]) -> tuple[CreditDecision, list[ProviderOffer]]:
    """Score a merchant once, then rank compatible provider offers."""
    decision = score_merchant_from_transactions(merchant_id, transactions)
    offers = []
    for profile in PROVIDER_PROFILES:
        eligible = (
            decision.risk_score <= profile.max_risk_score
            and decision.repayment_model in profile.repayment_models
        )
        offers.append(
            ProviderOffer(
                provider_id=profile.provider_id,
                provider_name=profile.name,
                eligible=eligible,
                offered_credit_limit=(
                    round(decision.recommended_credit_limit * profile.credit_multiplier, 2)
                    if eligible else 0
                ),
                repayment_model=decision.repayment_model if eligible else None,
                fit_score=round(max(0, 1 - decision.risk_score) * (profile.credit_multiplier if eligible else 0), 4),
                policy_version=profile.policy_version,
                estimated_fee_rate=profile.estimated_fee_rate,
                decision_sla_hours=profile.decision_sla_hours,
                data_requirements=list(profile.data_requirements),
                reason=_reason(profile, decision),
            )
        )
    offers.sort(key=lambda offer: (offer.eligible, offer.fit_score), reverse=True)
    return decision, offers


def aggregate_with_analysis(merchant_id: str, transactions: list[Transaction]):
    """Return the provider ranking together with the cash-flow analysis used by scoring."""
    decision, offers = aggregate_offers(merchant_id, transactions)
    return decision, analyze_cash_gaps(merchant_id, transactions), offers
