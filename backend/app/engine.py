"""Buyer-utility scoring used to rank vendors and pick the best deal.

Utility is denominated in ~$k/year so that real dollars dominate the decision
(the buyer's stated priority is lowest price). Non-price sweeteners are
monetized into modest annual-value bonuses rather than free-floating points.
"""
from __future__ import annotations

from .models import BuyerConfig, Offer, Vendor

_SUPPORT_VALUE_K = {"standard": 0.0, "priority": 3.0, "premium": 6.0}


def utility(buyer: BuyerConfig, vendor: Vendor, offer: Offer | None, walked: bool) -> float:
    """Higher = better deal for the buyer, in ~$k/year of effective value."""
    if not offer or walked:
        return -1e9
    annual = offer.annual_total(buyer.seats)
    score = -annual / 1000.0  # lower real cost wins
    score += _SUPPORT_VALUE_K[offer.support_tier]

    prios = " ".join(buyer.priorities).lower()
    if "flexible" in prios and offer.contract_length_months <= 12:
        score += 2.0
    if "long" in prios and offer.contract_length_months >= 24:
        score += 1.5
    if "support" in prios and offer.support_tier != "standard":
        score += 2.0
    return round(score, 2)
