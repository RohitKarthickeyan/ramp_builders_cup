"""Simulated 'online research' the buyer agent can run mid-negotiation.

Two capabilities:
  * discount_codes(vendor)   – promo / volume codes worth quoting
  * comparable_contracts(v)  – what peer companies reportedly paid

For the demo this returns curated, deterministic data so the presentation is
reliable and offline-capable. It is structured as a tool so a real web-search
backend (Vendr / G2 / Bing) could be dropped in behind the same interface.
"""
from __future__ import annotations

import re

from .models import ResearchFinding, ResearchReport, Vendor

# Curated, plausible market intel keyed by vendor id.
_DISCOUNTS: dict[str, list[ResearchFinding]] = {
    "cursor": [
        ResearchFinding(
            source="Cursor Business promo",
            text="Annual prepay + 100+ seats unlocks ~20% off Business list.",
            url="https://cursor.com/pricing",
            price_per_seat=32.0,
        ),
        ResearchFinding(
            source="Ramp partner code RAMPAI20",
            text="Startup/partner code stacks 20% off the first annual term.",
            url="https://cursor.com/enterprise",
        ),
    ],
    "claude": [
        ResearchFinding(
            source="Anthropic Team annual",
            text="Annual billing on Claude Team is ~16% cheaper than monthly.",
            url="https://www.anthropic.com/pricing",
            price_per_seat=37.5,
        ),
        ResearchFinding(
            source="Enterprise volume tier",
            text="150+ seats typically qualifies for custom enterprise pricing.",
            url="https://www.anthropic.com/enterprise",
        ),
    ],
    "codex": [
        ResearchFinding(
            source="OpenAI enterprise bundle",
            text="Existing API committed-use customers get seat credits toward Codex.",
            url="https://openai.com/enterprise",
            price_per_seat=33.0,
        ),
        ResearchFinding(
            source="Annual commit discount",
            text="12-month prepay commonly lands 15-18% under monthly list.",
            url="https://openai.com/chatgpt/pricing",
        ),
    ],
}

_COMPARABLES: dict[str, list[ResearchFinding]] = {
    "cursor": [
        ResearchFinding(source="Vendr benchmark", text="250-seat SaaS co. closed Cursor Business at $27/seat on annual.", url="https://www.vendr.com/marketplace/cursor", price_per_seat=27.0),
        ResearchFinding(source="G2 / peer report", text="Series-C fintech reported ~$25.50/seat at 300 seats.", url="https://www.g2.com/products/cursor", price_per_seat=25.5),
    ],
    "claude": [
        ResearchFinding(source="Vendr benchmark", text="Enterprise (400 seats) landed Claude Code near $31/seat.", url="https://www.vendr.com/marketplace/anthropic", price_per_seat=31.0),
        ResearchFinding(source="Peer procurement note", text="200-seat deal closed at $33/seat + priority support.", url="https://www.vendr.com/marketplace/anthropic", price_per_seat=33.0),
    ],
    "codex": [
        ResearchFinding(source="Vendr benchmark", text="Mid-market (220 seats) closed Codex around $29/seat.", url="https://www.vendr.com/marketplace/openai", price_per_seat=29.0),
        ResearchFinding(source="Peer report", text="Existing OpenAI customer got $27.50/seat with an API co-term.", url="https://www.vendr.com/marketplace/openai", price_per_seat=27.5),
    ],
}


def discount_codes(vendor: Vendor) -> ResearchReport:
    findings = _DISCOUNTS.get(vendor.id) or [
        ResearchFinding(
            source="General",
            text=f"Annual prepay usually beats monthly list for {vendor.name}.",
        )
    ]
    return ResearchReport(
        vendor_id=vendor.id,
        query=f"{vendor.name} discount codes & volume pricing",
        findings=findings,
    )


def comparable_contracts(vendor: Vendor) -> ResearchReport:
    findings = _COMPARABLES.get(vendor.id) or [
        ResearchFinding(
            source="General",
            text=f"Comparable {vendor.name} deals cluster ~20-30% under list at volume.",
        )
    ]
    return ResearchReport(
        vendor_id=vendor.id,
        query=f"What peers paid for {vendor.name} contracts",
        findings=findings,
    )


def best_comparable_price(report: ResearchReport) -> float | None:
    prices = [f.price_per_seat for f in report.findings if f.price_per_seat]
    return min(prices) if prices else None


_PCT_RE = re.compile(r"(\d{1,2})\s*%")


def best_discount_price(report: ResearchReport, list_price: float) -> tuple[float | None, str | None]:
    """Effective per-seat price the buyer could achieve via discount codes.

    Uses an explicit price when a finding provides one, otherwise derives it by
    applying any percentage discount mentioned in the text to the list price.
    Returns (best_price, source_label) so the agent can cite the specific code.
    """
    best_price: float | None = None
    best_label: str | None = None
    for f in report.findings:
        eff = f.price_per_seat
        if eff is None:
            m = _PCT_RE.search(f.text)
            if m:
                eff = round(list_price * (1 - int(m.group(1)) / 100), 2)
        if eff is not None and (best_price is None or eff < best_price):
            best_price, best_label = eff, f.source
    return best_price, best_label
