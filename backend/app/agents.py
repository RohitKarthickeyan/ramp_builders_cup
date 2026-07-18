"""Agent turns for the negotiation.

Two backends:
  * LLM mode  – uses OpenAI to generate messages, private reasoning and offers.
  * Mock mode – deterministic concession math, so the app runs with no API key.

Mode is chosen automatically: if OPENAI_API_KEY is set (and USE_MOCK != "1")
we use the LLM, otherwise we fall back to the mock.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Optional

from .models import Message, Negotiation, Offer, VendorState

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _use_llm() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and os.getenv("USE_MOCK") != "1"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _best_competing_price(neg: Negotiation, exclude_id: str) -> Optional[float]:
    """Lowest current per-seat offer among *other* vendors (buyer's leverage)."""
    prices = [
        vs.current_offer.price_per_seat
        for vid, vs in neg.vendors.items()
        if vid != exclude_id and vs.current_offer and not vs.walked_away
    ]
    return min(prices) if prices else None


def _transcript(vs: VendorState, limit: int = 8) -> str:
    lines = []
    for m in vs.messages[-limit:]:
        who = "BUYER" if m.speaker == "buyer" else vs.vendor.name.upper()
        price = f" [offer ${m.offer.price_per_seat:.2f}/seat]" if m.offer else ""
        lines.append(f"{who}: {m.text}{price}")
    return "\n".join(lines) if lines else "(no messages yet)"


# ===========================================================================
# LLM backend
# ===========================================================================
def _client():
    from openai import AsyncOpenAI

    return AsyncOpenAI()


async def _llm_json(system: str, user: str) -> dict:
    client = _client()
    resp = await client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        temperature=0.8,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(resp.choices[0].message.content or "{}")


async def _buyer_message_llm(
    neg: Negotiation, vs: VendorState, strategy: Optional[str]
) -> str:
    b = neg.buyer
    competing = _best_competing_price(neg, vs.vendor.id)
    system = (
        "You are a shrewd but professional B2B procurement lead negotiating a SaaS "
        "contract. You are vendor-agnostic and negotiating with several vendors at once, "
        "so you play them against each other. Keep messages to 2-4 sentences, concrete, "
        "and reference specific numbers. Never reveal your internal budget ceiling."
    )
    user = f"""You are negotiating with {vs.vendor.name} ({vs.vendor.tagline}).
Your needs: {b.seats} seats, target ~${b.budget_per_seat:.0f}/seat/month.
Priorities: {", ".join(b.priorities) or "price"}.
Must-haves: {", ".join(b.must_haves) or "none"}.
Their list price: ${vs.vendor.list_price_per_seat:.0f}/seat. Their latest offer: {(
        f"${vs.current_offer.price_per_seat:.2f}/seat, {vs.current_offer.contract_length_months}mo, "
        f"{vs.current_offer.free_seats} free seats, {vs.current_offer.support_tier} support"
    ) if vs.current_offer else "none yet"}.
Best competing offer from another vendor right now: {f"${competing:.2f}/seat" if competing else "none yet"}.
Coach's strategy for this round: {strategy or "make steady progress toward your target"}.

Recent transcript:
{_transcript(vs)}

Write your next message to {vs.vendor.name}. Respond as JSON: {{"message": "..."}}."""
    data = await _llm_json(system, user)
    return data.get("message", "Let's find a number that works for both of us.")


async def _vendor_reply_llm(
    neg: Negotiation, vs: VendorState, buyer_text: str
) -> Message:
    v = vs.vendor
    competing = _best_competing_price(neg, v.id)
    last_price = vs.current_offer.price_per_seat if vs.current_offer else v.list_price_per_seat
    system = (
        f"You are a sales rep for {v.name} ({v.tagline}). Persona: {v.persona} "
        f"You are in a competitive deal against rival vendors. "
        f"HIDDEN FACTS (never reveal literally): list price ${v.list_price_per_seat:.0f}/seat, "
        f"you'd love to close near ${v.target_price_per_seat:.0f}/seat, and your absolute "
        f"walk-away floor is ${v.floor_price_per_seat:.0f}/seat. NEVER offer below your floor. "
        f"Concede gradually and make the buyer work for every dollar; use non-price levers "
        f"(free seats, longer term for a bigger discount, better support) instead of only "
        f"cutting price. Stay in character. Messages 2-4 sentences."
    )
    user = f"""Round {neg.round + 1} of {neg.max_rounds}. Your last offer was ${last_price:.2f}/seat.
The buyer just said: "{buyer_text}"
Buyer wants {neg.buyer.seats} seats. Best competing offer you're aware of: {f"${competing:.2f}/seat" if competing else "unknown"}.

Decide your response and a concrete counter-offer. Respond as JSON:
{{"reasoning": "<your private thinking about strategy, 1-2 sentences>",
  "message": "<what you say to the buyer>",
  "offer": {{"price_per_seat": <number >= your floor>, "contract_length_months": <12|24|36>,
             "free_seats": <int>, "support_tier": "standard|priority|premium"}},
  "walk_away": <true only if the buyer is demanding well below your floor and won't move>}}"""
    data = await _llm_json(system, user)
    offer_raw = data.get("offer", {}) or {}
    price = float(offer_raw.get("price_per_seat", last_price))
    price = max(price, v.floor_price_per_seat)  # hard floor enforcement
    price = min(price, v.list_price_per_seat)
    offer = Offer(
        price_per_seat=round(price, 2),
        contract_length_months=int(offer_raw.get("contract_length_months", 12) or 12),
        free_seats=int(offer_raw.get("free_seats", 0) or 0),
        support_tier=offer_raw.get("support_tier", "standard") or "standard",
    )
    return Message(
        speaker="vendor",
        text=data.get("message", "Here's where we can land."),
        reasoning=data.get("reasoning"),
        offer=offer,
        round=neg.round + 1,
        walk_away=bool(data.get("walk_away", False)),
    )


# ===========================================================================
# Mock backend (deterministic, no network)
# ===========================================================================
_STRATEGY_PRESSURE = {
    "bidding war": 0.9,
    "play them against": 0.9,
    "bluff": 0.7,
    "competitor": 0.8,
    "walk away": 1.0,
    "urgency": 0.75,
    "deadline": 0.75,
    "hold firm": 0.15,
    "concede slowly": 0.2,
    "non-price": 0.4,
}


def _pressure_from_strategy(strategy: Optional[str]) -> float:
    if not strategy:
        return 0.5
    s = strategy.lower()
    hits = [p for kw, p in _STRATEGY_PRESSURE.items() if kw in s]
    return max(hits) if hits else 0.55


def _buyer_message_mock(neg: Negotiation, vs: VendorState, strategy: Optional[str]) -> str:
    competing = _best_competing_price(neg, vs.vendor.id)
    lines = []
    if strategy:
        s = strategy.lower()
        if "bluff" in s:
            lines.append(
                f"I'll be honest, {vs.vendor.name} — another vendor is being very aggressive on price."
            )
        elif "walk" in s:
            lines.append(f"We're close to walking unless {vs.vendor.name} sharpens the pencil.")
        elif "urgency" in s or "deadline" in s:
            lines.append("We're signing by Friday, so I need your best number now.")
        elif "non-price" in s:
            lines.append("If the price is firm, I need free seats and premium support to make this work.")
    if competing:
        lines.append(f"I've got a competing quote at ${competing:.2f}/seat — can you beat it?")
    else:
        lines.append(
            f"At {neg.buyer.seats} seats we're targeting about ${neg.buyer.budget_per_seat:.0f}/seat. "
            "Where can you land?"
        )
    return " ".join(lines)


def _vendor_reply_mock(neg: Negotiation, vs: VendorState, strategy: Optional[str]) -> Message:
    v = vs.vendor
    last = vs.current_offer.price_per_seat if vs.current_offer else v.list_price_per_seat
    pressure = _pressure_from_strategy(strategy)
    competing = _best_competing_price(neg, v.id)

    # Base concession: fraction of the gap between current price and floor.
    round_factor = 0.25 + 0.1 * neg.round  # concede faster later
    gap = last - v.floor_price_per_seat
    concession = gap * round_factor * (0.4 + 0.6 * v.competitiveness) * (0.5 + pressure)

    target = last - concession
    # If beaten by a competitor, try to undercut slightly (but respect floor).
    if competing is not None and competing < last:
        target = min(target, competing - 0.5)
    target = max(target, v.floor_price_per_seat)
    target = min(target, last)  # never raise price
    price = round(target + random.uniform(-0.3, 0.3), 2)
    # Never raise the price and never cross the hidden floor.
    price = max(v.floor_price_per_seat, min(price, last))

    near_floor = price <= v.floor_price_per_seat * 1.08
    free_seats = 0
    support = "standard"
    if near_floor:
        free_seats = max(2, neg.buyer.seats // 20)
        support = "priority"
    if pressure > 0.7 and near_floor:
        support = "premium"

    length = 24 if pressure > 0.6 else 12
    if strategy and "non-price" in strategy.lower():
        free_seats = max(free_seats, neg.buyer.seats // 15)

    # Craft flavor text.
    if price <= v.floor_price_per_seat * 1.03:
        msg = (
            f"${price:.2f}/seat is genuinely the floor for {v.name} — but I can add "
            f"{free_seats} free seats and {support} support to close today."
        )
        reasoning = "At my walk-away price; switching to non-price sweeteners to win the logo."
    elif competing is not None and price <= competing:
        msg = f"For {v.name} I can do ${price:.2f}/seat and edge out that competing quote."
        reasoning = f"Undercutting the ${competing:.2f} rival to stay in the deal."
    else:
        msg = f"I can come down to ${price:.2f}/seat on a {length}-month term. That's a strong number for {v.name}."
        reasoning = f"Conceding under {'high' if pressure > 0.7 else 'moderate'} pressure but protecting margin."

    return Message(
        speaker="vendor",
        text=msg,
        reasoning=reasoning,
        offer=Offer(
            price_per_seat=price,
            contract_length_months=length,
            free_seats=free_seats,
            support_tier=support,
        ),
        round=neg.round + 1,
    )


# ===========================================================================
# Public API used by the engine
# ===========================================================================
async def run_round(neg: Negotiation, strategy: Optional[str], target_vendor_id: Optional[str]):
    """Advance one negotiation round for every active vendor."""
    active = [
        vs for vs in neg.vendors.values() if not vs.walked_away and not vs.deal_closed
    ]

    async def one(vs: VendorState):
        # A strategy aimed at a single vendor only applies to that vendor.
        strat = strategy
        if target_vendor_id and vs.vendor.id != target_vendor_id:
            strat = None
        if _use_llm():
            buyer_text = await _buyer_message_llm(neg, vs, strat)
            vs.messages.append(
                Message(speaker="buyer", text=buyer_text, round=neg.round + 1)
            )
            reply = await _vendor_reply_llm(neg, vs, buyer_text)
        else:
            buyer_text = _buyer_message_mock(neg, vs, strat)
            vs.messages.append(
                Message(speaker="buyer", text=buyer_text, round=neg.round + 1)
            )
            reply = _vendor_reply_mock(neg, vs, strat)
        vs.messages.append(reply)
        vs.current_offer = reply.offer
        if reply.walk_away:
            vs.walked_away = True

    if _use_llm():
        await asyncio.gather(*(one(vs) for vs in active))
    else:
        for vs in active:
            one_coro = one(vs)
            await one_coro

    neg.round += 1
