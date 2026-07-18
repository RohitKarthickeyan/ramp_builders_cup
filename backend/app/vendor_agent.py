"""A vendor sales agent. Each vendor runs its own async loop: it watches its
inbox, waits a *variable* amount of time (personality-driven latency), then
drafts and sends a counter-offer email. Pricing respects a hidden floor.
"""
from __future__ import annotations

import os
import random

from . import llm
from .models import Email, Offer, Vendor

LATENCY_SCALE = float(os.getenv("LATENCY_SCALE", "1"))

_PRESSURE_KEYWORDS = {
    "walk": 0.95,
    "final": 0.8,
    "deadline": 0.8,
    "friday": 0.8,
    "competing": 0.85,
    "beat": 0.85,
    "cheaper": 0.8,
    "benchmark": 0.75,
    "budget": 0.6,
    "sign": 0.7,
}


def _pressure(body: str, ask_price: float | None, last_price: float) -> float:
    b = body.lower()
    hits = [p for kw, p in _PRESSURE_KEYWORDS.items() if kw in b]
    base = max(hits) if hits else 0.45
    if ask_price and ask_price < last_price:
        gap = (last_price - ask_price) / max(last_price, 1)
        base = min(1.0, base + gap)  # low-ball asks apply more pressure
    return base


class VendorAgent:
    def __init__(self, runtime, vendor: Vendor):
        self.rt = runtime
        self.v = vendor

    @property
    def state(self):
        return self.rt.vstate(self.v.id)

    async def run(self):
        while self.rt.running:
            await self.rt.wait_if_paused()
            if not self.rt.running:
                break
            for em in self.rt.mailbox.unread_for(self.v.id):
                self.rt.mailbox.mark_read(self.v.id, em.id)
                if self.rt.running:
                    await self._respond(em)
            await self.rt.sleep(0.4)

    async def _respond(self, buyer_email: Email):
        st = self.state
        if st.deal_closed or st.walked_away:
            return

        # Variable "thinking/typing" latency — this is what makes replies feel
        # live and lets the buyer's follow-up timer occasionally fire first.
        delay = random.uniform(self.v.reply_min_s, self.v.reply_max_s) * LATENCY_SCALE
        self.rt.set_agent_status(self.v.id, "reading", f"Reading {buyer_email.sender_name}'s email")
        await self.rt.broadcast()
        await self.rt.sleep(min(1.2, delay * 0.3))
        self.rt.set_agent_status(self.v.id, "drafting", "Drafting a counter-offer")
        await self.rt.broadcast()
        await self.rt.sleep(delay * 0.7)
        if not self.rt.running or st.deal_closed:
            return

        ask = buyer_email.offer.price_per_seat if buyer_email.offer else None
        offer = self._counter_offer(buyer_email.body, ask)
        st.last_price = offer.price_per_seat
        st.current_offer = offer
        st.turns += 1

        body = await self._draft_body(buyer_email, offer)
        self.rt.mailbox.send(
            thread_id=st.thread_id,
            vendor_id=self.v.id,
            subject=st.subject,
            sender_id=self.v.id,
            sender_role="vendor",
            sender_name=f"{self.v.name} Sales",
            to_id="buyer",
            to_name=self.rt.buyer.company + " Procurement",
            body=body,
            offer=offer,
        )
        st.awaiting_buyer = True
        self.rt.set_agent_status(self.v.id, "sent", f"Sent offer ${offer.price_per_seat:.2f}/seat")
        self.rt.log(self.v.id, f"{self.v.name} Sales", "email",
                    f"Replied with ${offer.price_per_seat:.2f}/seat, {offer.contract_length_months}mo.")
        await self.rt.broadcast()

    def _counter_offer(self, body: str, ask: float | None) -> Offer:
        v = self.v
        st = self.state
        last = st.last_price if st.last_price is not None else v.list_price_per_seat
        pressure = _pressure(body, ask, last)

        round_factor = 0.18 + 0.12 * st.turns
        gap = last - v.floor_price_per_seat
        concession = gap * round_factor * (0.4 + 0.6 * v.competitiveness) * (0.5 + pressure)
        target = last - concession

        # If the buyer quoted a credible lower number, drift toward it (but hold floor).
        if ask is not None and ask < last:
            target = min(target, max(ask + 0.75, v.floor_price_per_seat))

        target = max(target, v.floor_price_per_seat)
        target = min(target, last)  # never raise the price
        price = round(max(v.floor_price_per_seat, min(last, target + random.uniform(-0.25, 0.25))), 2)

        near_floor = price <= v.floor_price_per_seat * 1.06
        free_seats = 0
        support = "standard"
        length = 24 if pressure > 0.6 else 12
        if near_floor:
            free_seats = max(3, self.rt.buyer.seats // 20)
            support = "premium" if pressure > 0.7 else "priority"
        elif pressure > 0.55:
            free_seats = max(free_seats, self.rt.buyer.seats // 40)

        return Offer(
            price_per_seat=price,
            contract_length_months=length,
            free_seats=free_seats,
            support_tier=support,  # type: ignore[arg-type]
        )

    async def _draft_body(self, buyer_email: Email, offer: Offer) -> str:
        if llm.use_llm():
            data = await llm.json_call(
                system=(
                    f"You are a sales rep for {self.v.name} ({self.v.tagline}). "
                    f"Persona: {self.v.persona} Write a short (2-4 sentence) professional "
                    f"sales email replying to a procurement buyer. Reference the concrete "
                    f"offer numbers you're providing. Stay in character; be warm but protect margin. "
                    f"Never reveal you have a hidden floor."
                ),
                user=(
                    f"The buyer wrote:\n\"{buyer_email.body}\"\n\n"
                    f"Your new offer: ${offer.price_per_seat:.2f}/seat/mo, "
                    f"{offer.contract_length_months}-month term, {offer.free_seats} free seats, "
                    f"{offer.support_tier} support, for {self.rt.buyer.seats} seats.\n"
                    f'Respond as JSON: {{"body": "..."}}'
                ),
            )
            body = data.get("body")
            if body:
                return body
        return self._mock_body(offer)

    def _mock_body(self, offer: Offer) -> str:
        v = self.v
        greeting = f"Hi {self.rt.buyer.company} team,"
        terms = (
            f"we can do ${offer.price_per_seat:.2f}/seat/month on a "
            f"{offer.contract_length_months}-month term for {self.rt.buyer.seats} seats"
        )
        extras = []
        if offer.free_seats:
            extras.append(f"{offer.free_seats} seats on us")
        if offer.support_tier != "standard":
            extras.append(f"{offer.support_tier} support included")
        extra_str = (" We'll also throw in " + " and ".join(extras) + ".") if extras else ""
        if offer.price_per_seat <= v.floor_price_per_seat * 1.04:
            pitch = f"This is genuinely the sharpest {v.name} can go, but I want to win your business."
        elif v.competitiveness > 0.7:
            pitch = f"We really want to displace whatever you're using today, so {terms}."
            return f"{greeting} {pitch}{extra_str} Ready to move fast if you are.\n\n— {v.name} Sales"
        else:
            pitch = f"Happy to keep working toward a number that fits — for now {terms}."
        return f"{greeting} {pitch}{extra_str}\n\n— {v.name} Sales"
