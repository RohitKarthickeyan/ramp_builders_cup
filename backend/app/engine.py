"""Negotiation lifecycle: setup, scoring and winner selection."""
from __future__ import annotations

import uuid

from .models import (
    BuyerConfig,
    Negotiation,
    Offer,
    Vendor,
    VendorState,
)
from .scenarios import get_category


def start_negotiation(category_id: str, buyer: BuyerConfig | None) -> Negotiation:
    cat = get_category(category_id)
    buyer = buyer or BuyerConfig()
    vendors: dict[str, VendorState] = {}
    for v in cat["vendors"]:
        vendor: Vendor = v.model_copy(deep=True)
        # Opening offer: list price, standard terms.
        opening = Offer(
            price_per_seat=vendor.list_price_per_seat,
            contract_length_months=12,
            free_seats=0,
            support_tier="standard",
        )
        vendors[vendor.id] = VendorState(vendor=vendor, current_offer=opening)
    neg = Negotiation(
        id=uuid.uuid4().hex[:12],
        category=category_id,
        buyer=buyer,
        vendors=vendors,
    )
    return neg


def score_offer(neg: Negotiation, vs: VendorState) -> float:
    """Buyer-utility score (higher = better deal for the buyer).

    Combines price vs. budget with the buyer's stated priorities and non-price
    sweeteners. Used to rank vendors and decide the winner.
    """
    if not vs.current_offer or vs.walked_away:
        return -1e9
    o = vs.current_offer
    b = neg.buyer

    # Price component: how far under (or over) budget, normalized.
    price_delta = (b.budget_per_seat - o.price_per_seat) / max(b.budget_per_seat, 1)
    score = 100 * price_delta  # +ve if under budget

    # Savings vs list price (rewards hard-won discounts).
    discount = (vs.vendor.list_price_per_seat - o.price_per_seat) / vs.vendor.list_price_per_seat
    score += 40 * discount

    # Non-price value.
    score += o.free_seats * 1.5
    score += {"standard": 0, "priority": 5, "premium": 10}[o.support_tier]

    # Priority weighting.
    prios = " ".join(b.priorities).lower()
    if "flexible" in prios and o.contract_length_months <= 12:
        score += 8
    if "long" in prios and o.contract_length_months >= 24:
        score += 6
    if "support" in prios and o.support_tier != "standard":
        score += 6
    return round(score, 2)


def rank(neg: Negotiation) -> list[tuple[str, float]]:
    scored = [(vid, score_offer(neg, vs)) for vid, vs in neg.vendors.items()]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def finish(neg: Negotiation, close_vendor_id: str | None = None) -> Negotiation:
    if close_vendor_id and close_vendor_id in neg.vendors:
        winner_id = close_vendor_id
    else:
        ranked = rank(neg)
        winner_id = ranked[0][0] if ranked else None
    neg.winner_id = winner_id
    neg.finished = True
    if winner_id:
        neg.vendors[winner_id].deal_closed = True
    return neg


def scorecard(neg: Negotiation) -> dict:
    """Summary for the end screen."""
    ranked = rank(neg)
    rows = []
    for vid, sc in ranked:
        vs = neg.vendors[vid]
        o = vs.current_offer
        list_annual = round(vs.vendor.list_price_per_seat * neg.buyer.seats * 12, 2)
        annual = o.annual_total(neg.buyer.seats) if o else None
        rows.append(
            {
                "vendor_id": vid,
                "name": vs.vendor.name,
                "score": sc,
                "final_price_per_seat": o.price_per_seat if o else None,
                "contract_length_months": o.contract_length_months if o else None,
                "free_seats": o.free_seats if o else 0,
                "support_tier": o.support_tier if o else None,
                "annual_total": annual,
                "list_annual_total": list_annual,
                "savings": round(list_annual - annual, 2) if annual is not None else 0,
                "savings_pct": round(100 * (list_annual - annual) / list_annual, 1)
                if annual
                else 0,
                "walked_away": vs.walked_away,
            }
        )
    winner = next((r for r in rows if r["vendor_id"] == neg.winner_id), rows[0] if rows else None)
    return {"winner": winner, "rows": rows}
