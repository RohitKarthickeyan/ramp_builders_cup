"""The buyer (procurement) agent — the 'strategy brain'.

It runs an OODA-style loop over the shared inbox:
  Observe  – read new vendor emails, parse offers.
  Orient   – update a belief model per vendor (estimated floor, momentum),
             optionally run online research for leverage.
  Decide   – pick/keep a tactic (coached or auto) and a concrete counter-ask.
  Act       – draft & send an email, follow up on slow vendors, or, once the
             field has converged, draft a contract for human approval.
"""
from __future__ import annotations

import random

from . import llm, research
from .models import Belief, Email, Offer, Strategy


class BuyerAgent:
    NAME = "Ramp Procurement Agent"

    def __init__(self, runtime):
        self.rt = runtime
        self._opened = False

    # -- lifecycle -----------------------------------------------------------
    async def run(self):
        await self._open_rfp()
        while self.rt.running:
            await self.rt.wait_if_paused()
            if not self.rt.running:
                break
            await self._tick()
            await self.rt.sleep(1.0)

    async def _open_rfp(self):
        if self._opened:
            return
        self._opened = True
        b = self.rt.buyer
        self.rt.set_agent_status("buyer", "drafting", "Sending opening RFP to all vendors")
        self.rt.log("buyer", self.NAME, "action",
                    f"Kicking off: {b.seats} seats, target ${b.budget_per_seat:.0f}/seat. Emailing all vendors.")
        await self.rt.broadcast()
        for v in self.rt.vendors:
            bs = self.rt.bstate(v.id)
            ask = round(b.budget_per_seat * 0.92, 2)  # anchor a touch under target
            body = (
                f"Hi {v.name} team,\n\n{b.company} is evaluating AI coding assistants for "
                f"{b.seats} engineers and {v.name} is on our shortlist. We're running a "
                f"competitive process. To be candid, our budget lands around "
                f"${b.budget_per_seat:.0f}/seat/month on an annual commit — can you get us to "
                f"${ask:.2f}/seat? Priorities: {', '.join(b.priorities)}.\n\n— {b.company} Procurement"
            )
            self.rt.mailbox.send(
                thread_id=bs.thread_id, vendor_id=v.id, subject=bs.subject,
                sender_id="buyer", sender_role="buyer", sender_name=self.NAME,
                to_id=v.id, to_name=f"{v.name} Sales", body=body,
                offer=Offer(price_per_seat=ask, contract_length_months=12),
            )
            bs.turns += 1
            bs.awaiting_reply = True
            bs.last_sent_ts = self.rt.clock()
            bs.followup_deadline = bs.last_sent_ts + random.uniform(7, 12)
        self.rt.set_agent_status("buyer", "waiting", "Waiting for vendor replies")
        await self.rt.broadcast()

    # -- main step -----------------------------------------------------------
    async def _tick(self):
        # Coaching is applied immediately by the runtime; we just read strategy.
        # Observe: process any new vendor replies.
        replied = False
        for em in self.rt.mailbox.unread_for("buyer"):
            self.rt.mailbox.mark_read("buyer", em.id)
            self._observe(em)
            replied = True
        if replied:
            await self.rt.broadcast()

        if self.rt.phase == "awaiting_approval":
            return

        # Decide whether the field has converged enough to close.
        if self._should_close():
            await self._draft_contract()
            return

        # Act on each active vendor.
        for v in self.rt.vendors:
            bs = self.rt.bstate(v.id)
            st = self.rt.vstate(v.id)
            if st.walked_away or st.deal_closed:
                continue
            if bs.needs_response and bs.turns < self.rt.max_turns:
                await self._respond_to_vendor(v)
            elif bs.awaiting_reply and self.rt.clock() > bs.followup_deadline and bs.followups < 2:
                await self._follow_up(v)

    # -- observe / orient ----------------------------------------------------
    def _observe(self, em: Email):
        v = self.rt.vendor_by_id(em.sender_id)
        if not v or not em.offer:
            return
        bs = self.rt.bstate(v.id)
        st = self.rt.vstate(v.id)
        p = em.offer.price_per_seat
        b: Belief = bs.belief

        if b.last_price is None:
            b.est_floor = round(v.list_price_per_seat * 0.72, 2)
        momentum = round((b.last_price if b.last_price is not None else v.list_price_per_seat) - p, 2)
        b.momentum = momentum
        if momentum < 0.4:  # barely moved → they're near their floor
            b.stalled_turns += 1
            b.est_floor = max(b.est_floor, round(p - 0.5, 2))
        else:
            b.stalled_turns = 0
            b.est_floor = min(b.est_floor, round(p - momentum * 0.8, 2))
        b.est_floor = round(min(max(b.est_floor, self.rt.buyer.budget_per_seat * 0.6), p), 2)
        b.confidence = round(min(1.0, b.confidence + 0.18 + (0.08 if momentum < 0.4 else 0.0)), 2)
        b.last_price = p

        bs.awaiting_reply = False
        bs.needs_response = True
        note = ("holding near floor" if b.stalled_turns else f"conceded ${momentum:.2f}")
        self.rt.log("buyer", self.NAME, "reasoning",
                    f"{v.name} → ${p:.2f}/seat ({note}). Est. floor ~${b.est_floor:.2f}, "
                    f"confidence {int(b.confidence*100)}%.")

    # -- decide: closing ------------------------------------------------------
    def _vendor_settled(self, vid: str) -> bool:
        bs = self.rt.bstate(vid)
        st = self.rt.vstate(vid)
        if not st.current_offer:
            return False
        price = st.current_offer.price_per_seat
        return (
            price <= self.rt.buyer.budget_per_seat * 1.02
            or bs.belief.stalled_turns >= 2
            or bs.turns >= self.rt.max_turns
        )

    def _should_close(self) -> bool:
        active = [v for v in self.rt.vendors if not self.rt.vstate(v.id).walked_away]
        have_offers = [v for v in active if self.rt.vstate(v.id).current_offer]
        if len(have_offers) < len(active):
            return False  # still waiting on someone's first reply
        # Close once every active vendor has settled, or we blew past a global cap.
        if all(self._vendor_settled(v.id) for v in active):
            return True
        total_turns = sum(self.rt.bstate(v.id).turns for v in active)
        return total_turns >= self.rt.max_turns * len(active)

    async def _draft_contract(self):
        winner_id, rows = self.rt.rank_vendors()
        if not winner_id:
            return
        v = self.rt.vendor_by_id(winner_id)
        self.rt.set_agent_status("buyer", "drafting", f"Drafting contract with {v.name}")
        self.rt.log("buyer", self.NAME, "action",
                    f"Field converged. Best deal: {v.name}. Drafting contract for human approval.")
        await self.rt.broadcast()
        await self.rt.sleep(1.5)
        self.rt.build_contract(winner_id)
        self.rt.set_phase("awaiting_approval")
        self.rt.set_agent_status("buyer", "blocked", "Awaiting human approval of contract")
        self.rt.log("buyer", self.NAME, "action", "Contract drafted. Paused for your approval.")
        await self.rt.broadcast()

    # -- act: emails ----------------------------------------------------------
    async def _maybe_research(self, v):
        bs = self.rt.bstate(v.id)
        if bs.researched or bs.turns > 2:
            return
        bs.researched = True
        self.rt.set_agent_status("buyer", "researching", f"Researching {v.name} pricing online")
        self.rt.log("buyer", self.NAME, "research", f"Searching market benchmarks & discount codes for {v.name}…")
        await self.rt.broadcast()
        await self.rt.sleep(random.uniform(1.5, 3.0))
        comp = research.comparable_contracts(v)
        disc = research.discount_codes(v)
        self.rt.add_research(comp)
        self.rt.add_research(disc)
        best = research.best_comparable_price(comp)
        bs.research_price = best
        disc_price, disc_label = research.best_discount_price(disc, v.list_price_per_seat)
        bs.discount_price = disc_price
        bs.discount_label = disc_label
        summary = f"Found peer benchmarks for {v.name}"
        if best:
            summary += f" (~${best:.2f}/seat)"
        if disc_price:
            summary += f"; best discount → ${disc_price:.2f}/seat via {disc_label}"
        self.rt.log("buyer", self.NAME, "research", summary + ".")
        await self.rt.broadcast()

    def _coach_price(self, vid: str) -> float | None:
        """The explicit price the coach demanded, if it applies to this vendor."""
        strat = self.rt.strategy
        if strat.target_price is None:
            return None
        if strat.target_vendor_id and strat.target_vendor_id != vid:
            return None
        return strat.target_price

    def _leverage_price(self, vid: str) -> float | None:
        """Best credible number to quote against this vendor: the lowest of a
        rival's current offer, a researched comparable price, an achievable
        discount-code price, and any explicit number the coach handed us."""
        candidates = []
        comp = self.rt.best_competing_price(vid)
        if comp:
            candidates.append(comp)
        bs = self.rt.bstate(vid)
        if bs.research_price:
            candidates.append(bs.research_price)
        if bs.discount_price:
            candidates.append(bs.discount_price)
        coach = self._coach_price(vid)
        if coach is not None:
            candidates.append(coach)
        return min(candidates) if candidates else None

    def _counter_ask(self, v, tactic: str) -> float:
        b = self.rt.buyer
        bs = self.rt.bstate(v.id)
        cur = self.rt.vstate(v.id).current_offer.price_per_seat

        # If the coach handed us an explicit number, honor it directly (this
        # overrides the agent's own reasoning and the credibility clamp).
        coach = self._coach_price(v.id)
        if coach is not None:
            return round(min(coach, cur), 2)

        # Otherwise the agent reasons about its own target from budget + belief.
        aim = max(b.budget_per_seat, bs.belief.est_floor)
        ask = cur - max(0.75, (cur - aim) * 0.6)
        if tactic in ("cross_leverage", "bluff", "deadline", "walk_away"):
            ref = self._leverage_price(v.id)
            if ref:
                ask = min(ask, ref - 0.5)
        if tactic == "hold_firm":
            ask = min(cur, b.budget_per_seat)
        ask = max(ask, b.budget_per_seat * 0.8)  # keep it credible
        return round(min(ask, cur), 2)

    async def _respond_to_vendor(self, v):
        bs = self.rt.bstate(v.id)
        bs.needs_response = False
        await self._maybe_research(v)

        strat: Strategy = self.rt.strategy
        tactic = strat.tactic
        if strat.target_vendor_id and strat.target_vendor_id != v.id:
            tactic = "anchor"  # coaching aimed elsewhere; stay neutral here

        ask = self._counter_ask(v, tactic)
        self.rt.set_agent_status("buyer", "drafting", f"Replying to {v.name} ({tactic.replace('_',' ')})")
        await self.rt.broadcast()
        await self.rt.sleep(random.uniform(0.8, 1.8))

        body = await self._draft_email(v, tactic, ask)
        self.rt.mailbox.send(
            thread_id=bs.thread_id, vendor_id=v.id, subject=bs.subject,
            sender_id="buyer", sender_role="buyer", sender_name=self.NAME,
            to_id=v.id, to_name=f"{v.name} Sales", body=body,
            offer=Offer(price_per_seat=ask, contract_length_months=12),
        )
        bs.turns += 1
        bs.awaiting_reply = True
        bs.last_sent_ts = self.rt.clock()
        bs.followup_deadline = bs.last_sent_ts + random.uniform(7, 12)
        self.rt.set_agent_status("buyer", "waiting", f"Waiting on {v.name}")
        self.rt.log("buyer", self.NAME, "email", f"Emailed {v.name}: pushing to ${ask:.2f}/seat via {tactic.replace('_',' ')}.")
        await self.rt.broadcast()

    async def _follow_up(self, v):
        bs = self.rt.bstate(v.id)
        bs.followups += 1
        bs.followup_deadline = self.rt.clock() + random.uniform(8, 14)
        self.rt.set_agent_status("buyer", "drafting", f"Following up with {v.name}")
        await self.rt.broadcast()
        await self.rt.sleep(random.uniform(0.6, 1.2))
        body = (
            f"Hi {v.name} team — following up on my note below. We're moving quickly and "
            f"lining up final numbers from the others this week. Where can you land?\n\n— {self.rt.buyer.company} Procurement"
        )
        self.rt.mailbox.send(
            thread_id=bs.thread_id, vendor_id=v.id, subject=bs.subject,
            sender_id="buyer", sender_role="buyer", sender_name=self.NAME,
            to_id=v.id, to_name=f"{v.name} Sales", body=body, is_followup=True,
        )
        bs.last_sent_ts = self.rt.clock()
        self.rt.log("buyer", self.NAME, "action", f"{v.name} was slow to respond — sent a nudge.")
        await self.rt.broadcast()

    async def _draft_email(self, v, tactic: str, ask: float) -> str:
        if llm.use_llm():
            data = await llm.json_call(
                system=(
                    "You are a shrewd, professional B2B procurement lead running a competitive "
                    "SaaS negotiation across several vendors at once. Keep it to 2-4 sentences, "
                    "concrete, reference specific numbers. Never reveal your true budget ceiling."
                ),
                user=(
                    f"Vendor: {v.name}. Their latest price: ${self.rt.vstate(v.id).current_offer.price_per_seat:.2f}/seat.\n"
                    f"Best competing/benchmark number you can cite: {self._leverage_price(v.id)}\n"
                    f"Your tactic this email: {tactic}.\n"
                    f"You want to push them to ~${ask:.2f}/seat for {self.rt.buyer.seats} seats.\n"
                    f'Write the email. Respond as JSON: {{"body": "..."}}'
                ),
            )
            if data.get("body"):
                return data["body"]
        return self._mock_email(v, tactic, ask)

    def _mock_email(self, v, tactic: str, ask: float) -> str:
        b = self.rt.buyer
        bs = self.rt.bstate(v.id)
        ref = self._leverage_price(v.id)
        # A bluff quotes a competitor at the leverage number (coach-fabricated if given).
        bluff_ref = ref if ref else round(ask, 2)
        lines = {
            "anchor": f"We need to get to ${ask:.2f}/seat to move forward with {v.name}.",
            "cross_leverage": (
                f"I've got a competing quote at ${ref:.2f}/seat." if ref else
                "Other vendors are coming in lower."
            ) + f" Beat it and the deal is yours at ${ask:.2f}/seat.",
            "bluff": f"Frankly a competing vendor just came in at ${bluff_ref:.2f}/seat — I need {v.name} at ${ask:.2f}/seat to stay in this.",
            "deadline": f"We're signing by Friday. Your best-and-final at ${ask:.2f}/seat gets it done.",
            "squeeze_non_price": f"If ${ask:.2f}/seat is a stretch, make it work with free seats and premium support.",
            "hold_firm": f"${ask:.2f}/seat is our number. We're happy with {v.name} but won't go above it.",
            "walk_away": f"We're prepared to walk unless {v.name} can reach ${ask:.2f}/seat.",
        }
        pitch = lines.get(tactic, lines["anchor"])
        cite = ""
        if tactic == "cross_leverage" and ref:
            # Attribute the number to a discount code when that's what drove it.
            if bs.discount_price is not None and abs(ref - bs.discount_price) < 0.01 and bs.discount_label:
                cite = f" ({bs.discount_label} gets us there.)"
            else:
                cite = " (peer benchmarks back this up.)"
        return f"Hi {v.name} team,\n\n{pitch}{cite}\n\n— {b.company} Procurement"
