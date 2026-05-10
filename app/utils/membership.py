from __future__ import annotations

from app.models import Membership

PRICE_BY_PLAN: dict[str, float] = {
    'mensual': 119900.0,
    'quincenal': 69900.0,
    'semanal': 44950.0,
    'anual': 299900.0,
}


def effective_membership_price(membership: Membership) -> float:
    stored_price = float(membership.price or 0)
    if stored_price > 0:
        return stored_price

    plan_key = (membership.plan or '').strip().lower()
    return float(PRICE_BY_PLAN.get(plan_key, 0.0))

