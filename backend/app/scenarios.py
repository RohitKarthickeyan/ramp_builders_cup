"""Preset negotiation categories with grounded-ish SaaS pricing.

Prices are monthly-per-seat in USD and are illustrative. Hidden target/floor
prices give each vendor room to move so negotiations don't collapse instantly.
"""
from __future__ import annotations

from .models import Vendor

CATEGORIES: dict[str, dict] = {
    "coding": {
        "label": "AI Coding Assistants",
        "description": "You're rolling out an AI coding tool to your engineers. You're vendor-agnostic.",
        "vendors": [
            Vendor(
                id="cursor",
                name="Cursor",
                tagline="The AI code editor",
                persona="Scrappy, fast-moving challenger. Hungry for logo wins and will "
                "discount aggressively to displace an incumbent, but proud of the product.",
                color="#7c5cff",
                list_price_per_seat=40,
                target_price_per_seat=32,
                floor_price_per_seat=22,
                competitiveness=0.8,
            ),
            Vendor(
                id="claude",
                name="Claude Code",
                tagline="Anthropic's agentic coder",
                persona="Premium, safety-forward, confident in quality. Holds price well and "
                "prefers to add value (support, seats) over cutting the sticker price.",
                color="#d4a27f",
                list_price_per_seat=45,
                target_price_per_seat=38,
                floor_price_per_seat=30,
                competitiveness=0.45,
            ),
            Vendor(
                id="codex",
                name="Codex",
                tagline="OpenAI's coding agent",
                persona="Incumbent-scale player, often already bundled with an enterprise "
                "agreement. Calm, leans on ecosystem lock-in, moderate flexibility.",
                color="#10a37f",
                list_price_per_seat=42,
                target_price_per_seat=35,
                floor_price_per_seat=26,
                competitiveness=0.6,
            ),
        ],
    },
    "chat": {
        "label": "Team Chat / Collaboration",
        "description": "You're picking a company-wide messaging platform. Any of the three works.",
        "vendors": [
            Vendor(
                id="slack",
                name="Slack",
                tagline="Where work happens",
                persona="Beloved challenger with strong user preference. Will fight to win but "
                "knows it's the pricier option; leans on stickiness and integrations.",
                color="#611f69",
                list_price_per_seat=15,
                target_price_per_seat=12,
                floor_price_per_seat=8,
                competitiveness=0.75,
            ),
            Vendor(
                id="teams",
                name="Microsoft Teams",
                tagline="Bundled with M365",
                persona="Incumbent giant. Often nearly free inside an existing Microsoft "
                "agreement; low urgency, will happily bundle rather than discount cash.",
                color="#4b53bc",
                list_price_per_seat=8,
                target_price_per_seat=6,
                floor_price_per_seat=3,
                competitiveness=0.4,
            ),
            Vendor(
                id="google",
                name="Google Chat",
                tagline="Part of Workspace",
                persona="Volume-discount giant. Flexible on price at scale, pushes multi-year "
                "Workspace commitments in exchange for steep per-seat cuts.",
                color="#1a73e8",
                list_price_per_seat=12,
                target_price_per_seat=9,
                floor_price_per_seat=5,
                competitiveness=0.65,
            ),
        ],
    },
}


def get_category(category_id: str) -> dict:
    if category_id not in CATEGORIES:
        raise KeyError(f"Unknown category '{category_id}'")
    return CATEGORIES[category_id]


def categories_public() -> list[dict]:
    """Lightweight list for the setup screen."""
    out = []
    for cid, cat in CATEGORIES.items():
        out.append(
            {
                "id": cid,
                "label": cat["label"],
                "description": cat["description"],
                "vendors": [v.public_view() for v in cat["vendors"]],
            }
        )
    return out
