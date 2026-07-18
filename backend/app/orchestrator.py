"""The live negotiation runtime.

Runs the buyer agent and every vendor agent as concurrent asyncio tasks that
communicate through the simulated mailbox. Broadcasts a full state snapshot to
any connected WebSocket clients after every meaningful step, so the dashboard
renders the negotiation as it happens. Supports live coaching, pause/stop and
human approval of the final contract.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Optional

from . import contract as contract_mod
from . import engine
from .buyer_agent import BuyerAgent
from .models import (
    Belief,
    BuyerConfig,
    Contract,
    LogEntry,
    Offer,
    ResearchReport,
    Strategy,
    Vendor,
)
from .vendor_agent import VendorAgent

DEFAULT_MAX_TURNS = 5


class VendorRT:
    def __init__(self, vendor: Vendor, thread_id: str, subject: str):
        self.vendor = vendor
        self.thread_id = thread_id
        self.subject = subject
        self.current_offer: Optional[Offer] = None
        self.last_price: Optional[float] = None
        self.turns = 0
        self.walked_away = False
        self.deal_closed = False
        self.awaiting_buyer = False


class BuyerVendorRT:
    def __init__(self, vendor_id: str, thread_id: str, subject: str):
        self.thread_id = thread_id
        self.subject = subject
        self.turns = 0
        self.needs_response = False
        self.awaiting_reply = False
        self.last_sent_ts = 0.0
        self.followup_deadline = 1e18
        self.followups = 0
        self.researched = False
        self.research_price: Optional[float] = None
        self.discount_price: Optional[float] = None
        self.discount_label: Optional[str] = None
        self.belief = Belief(vendor_id=vendor_id, est_floor=0.0)


def _tactic_from_text(text: str) -> tuple[str, str]:
    t = text.lower()
    table = [
        (("walk", "walk away"), "walk_away", "Signal we're ready to walk to force their floor."),
        (("bluff",), "bluff", "Imply a stronger competing offer than we actually hold."),
        (("deadline", "urgen", "friday", "sign by"), "deadline", "Apply time pressure to force best-and-final."),
        (("bidding", "against each other", "competitor", "leverage", "play them"), "cross_leverage", "Quote rivals against each other to drive price down."),
        (("support", "free seat", "non-price", "sweeten", "extras"), "squeeze_non_price", "Hold price, extract free seats and premium support."),
        (("hold", "firm", "stand"), "hold_firm", "Hold our number and make them move."),
        (("anchor", "aggressive", "low"), "anchor", "Anchor hard near our target."),
    ]
    for kws, tactic, rationale in table:
        if any(k in t for k in kws):
            return tactic, rationale
    return "cross_leverage", "Pursue the coach's guidance while playing vendors off each other."


# Skip numbers that are clearly not a per-seat price (terms, seat counts, %).
_PRICE_RE = re.compile(r"\$?\s*(\d{1,3}(?:\.\d{1,2})?)(?!\s*(?:%|mo|month|yr|year|seat|k\b))", re.I)


def _price_from_text(text: str) -> Optional[float]:
    """Pull an explicit per-seat price out of coaching text, if the coach gave one."""
    for m in _PRICE_RE.finditer(text):
        val = float(m.group(1))
        # A credible monthly per-seat SaaS price; ignores stray small/large numbers.
        if 3 <= val <= 300:
            return round(val, 2)
    return None


class NegotiationRuntime:
    def __init__(self, neg_id: str, buyer: BuyerConfig, vendors: list[Vendor], mode: str):
        from .mailbox import Mailbox

        self.id = neg_id
        self.buyer = buyer
        self.vendors = vendors
        self.mode = mode
        self.mailbox = Mailbox()
        self.max_turns = DEFAULT_MAX_TURNS

        self._vrt: dict[str, VendorRT] = {}
        self._brt: dict[str, BuyerVendorRT] = {}
        for v in vendors:
            tid = f"th_{v.id}"
            subj = f"{buyer.company} × {v.name} — AI coding assistant pricing"
            self._vrt[v.id] = VendorRT(v, tid, subj)
            self._brt[v.id] = BuyerVendorRT(v.id, tid, subj)

        self.strategy = Strategy()
        self.phase = "idle"  # idle | negotiating | awaiting_approval | done
        self.running = False
        self.paused = False
        self.logs: list[LogEntry] = []
        self.research: list[ResearchReport] = []
        self.contract: Optional[Contract] = None
        self.winner_id: Optional[str] = None
        self.summary: Optional[str] = None
        self.status: dict[str, tuple[str, str]] = {
            "buyer": ("idle", "Ready"),
            **{v.id: ("idle", "Standing by") for v in vendors},
        }

        self._subscribers: set[asyncio.Queue] = set()
        self._tasks: list[asyncio.Task] = []
        self._t0 = time.monotonic()

    # -- accessors used by agents -------------------------------------------
    def vstate(self, vid: str) -> VendorRT:
        return self._vrt[vid]

    def bstate(self, vid: str) -> BuyerVendorRT:
        return self._brt[vid]

    def vendor_by_id(self, vid: str) -> Optional[Vendor]:
        return next((v for v in self.vendors if v.id == vid), None)

    def clock(self) -> float:
        return time.monotonic()

    def best_competing_price(self, exclude_id: str) -> Optional[float]:
        prices = [
            rt.current_offer.price_per_seat
            for vid, rt in self._vrt.items()
            if vid != exclude_id and rt.current_offer and not rt.walked_away
        ]
        return min(prices) if prices else None

    def add_research(self, report: ResearchReport) -> None:
        self.research.append(report)

    def set_agent_status(self, agent_id: str, status: str, activity: str) -> None:
        self.status[agent_id] = (status, activity)

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def log(self, agent_id: str, agent_name: str, kind: str, text: str) -> None:
        self.logs.append(LogEntry(agent_id=agent_id, agent_name=agent_name, kind=kind, text=text))  # type: ignore[arg-type]
        if len(self.logs) > 400:
            self.logs = self.logs[-400:]

    # -- coaching / controls -------------------------------------------------
    async def apply_coaching(self, text: str) -> None:
        tactic, rationale = _tactic_from_text(text)
        target = None
        for v in self.vendors:
            if v.name.lower() in text.lower() or v.id in text.lower():
                target = v.id
                break
        price = _price_from_text(text)
        if price is not None:
            rationale += f" Push to ${price:.2f}/seat (coach-specified)."
        self.strategy = Strategy(
            tactic=tactic,  # type: ignore[arg-type]
            rationale=rationale,
            target_vendor_id=target,
            target_price=price,
            source="coaching",
        )
        who = f" (targeting {self.vendor_by_id(target).name})" if target else ""
        num = f" @ ${price:.2f}/seat" if price is not None else ""
        self.log("coach", "You (Coach)", "coaching", f"“{text}” → {tactic.replace('_',' ')}{who}{num}.")
        detail = f"New strategy: {tactic.replace('_',' ')}{num} — {rationale}"
        self.log("buyer", BuyerAgent.NAME, "strategy", detail)
        await self.broadcast()

    async def pause(self) -> None:
        self.paused = True
        self.log("buyer", BuyerAgent.NAME, "system", "Paused by operator.")
        await self.broadcast()

    async def resume(self) -> None:
        self.paused = False
        self.log("buyer", BuyerAgent.NAME, "system", "Resumed.")
        await self.broadcast()

    async def stop(self) -> None:
        self.running = False
        self.phase = "done" if self.phase != "done" else self.phase
        await self.broadcast()

    async def approve_contract(self) -> None:
        if not self.contract:
            return
        self.contract.status = "approved"
        vid = self.contract.vendor_id
        self._vrt[vid].deal_closed = True
        self.winner_id = vid
        self.phase = "done"
        self.running = False
        self.summary = (
            f"Signed {self.contract.vendor_name} at ${self.contract.price_per_seat:.2f}/seat — "
            f"${self.contract.savings:,.0f}/yr saved ({self.contract.savings_pct:.0f}% under list)."
        )
        self.set_agent_status("buyer", "done", "Contract approved & signed")
        self.log("buyer", BuyerAgent.NAME, "action", self.summary)
        await self.broadcast()

    async def reject_contract(self, note: str) -> None:
        if not self.contract:
            return
        self.contract = None
        self.phase = "negotiating"
        self.max_turns += 2
        for v in self.vendors:
            bs = self._brt[v.id]
            if not self._vrt[v.id].walked_away:
                bs.needs_response = True
                bs.belief.stalled_turns = 0
        self.log("coach", "You (Coach)", "coaching", f"Rejected draft: {note or 'push for a better deal'}")
        if note:
            await self.apply_coaching(note)
        else:
            self.set_agent_status("buyer", "drafting", "Re-opening negotiations")
            await self.broadcast()

    # -- deal selection / contract ------------------------------------------
    def rank_vendors(self):
        rows = []
        for v in self.vendors:
            rt = self._vrt[v.id]
            u = engine.utility(self.buyer, v, rt.current_offer, rt.walked_away)
            rows.append((v.id, u))
        rows.sort(key=lambda x: x[1], reverse=True)
        winner = rows[0][0] if rows and rows[0][1] > -1e8 else None
        return winner, rows

    def build_contract(self, vendor_id: str) -> Contract:
        v = self.vendor_by_id(vendor_id)
        offer = self._vrt[vendor_id].current_offer
        self.contract = contract_mod.build(self.buyer, v, offer)
        self.winner_id = vendor_id
        return self.contract

    # -- timing helpers ------------------------------------------------------
    async def sleep(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while self.running and time.monotonic() < end:
            await asyncio.sleep(min(0.2, max(0.0, end - time.monotonic())))

    async def wait_if_paused(self) -> None:
        while self.paused and self.running:
            await asyncio.sleep(0.2)

    # -- pub/sub -------------------------------------------------------------
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def broadcast(self) -> None:
        snap = {"type": "state", "state": self.snapshot()}
        for q in list(self._subscribers):
            try:
                q.put_nowait(snap)
            except Exception:
                self._subscribers.discard(q)

    # -- start ---------------------------------------------------------------
    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.phase = "negotiating"
        buyer_agent = BuyerAgent(self)
        self._tasks.append(asyncio.create_task(self._safe(buyer_agent.run(), "buyer")))
        for v in self.vendors:
            va = VendorAgent(self, v)
            self._tasks.append(asyncio.create_task(self._safe(va.run(), v.id)))

    async def _safe(self, coro, who: str) -> None:
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception as e:  # keep the dashboard alive if one agent errors
            self.log(who, who, "system", f"Agent error: {type(e).__name__}: {str(e)[:120]}")
            await self.broadcast()

    # -- snapshot ------------------------------------------------------------
    def _price_history(self, vid: str) -> list[float]:
        v = self.vendor_by_id(vid)
        hist = [v.list_price_per_seat]
        thread = self.mailbox.threads.get(f"th_{vid}")
        if thread:
            for em in thread.emails:
                if em.sender_role == "vendor" and em.offer:
                    hist.append(em.offer.price_per_seat)
        return hist

    def snapshot(self) -> dict:
        agents = [
            {
                "id": "buyer",
                "kind": "buyer",
                "name": BuyerAgent.NAME,
                "color": "#7c5cff",
                "status": self.status["buyer"][0],
                "activity": self.status["buyer"][1],
            }
        ]
        for v in self.vendors:
            rt = self._vrt[v.id]
            bs = self._brt[v.id]
            st, act = self.status[v.id]
            agents.append(
                {
                    "id": v.id,
                    "kind": "vendor",
                    "name": v.name,
                    "tagline": v.tagline,
                    "persona": v.persona,
                    "color": v.color,
                    "status": st,
                    "activity": act,
                    "list_price_per_seat": v.list_price_per_seat,
                    "current_offer": rt.current_offer.model_dump() if rt.current_offer else None,
                    "price_history": self._price_history(v.id),
                    "walked_away": rt.walked_away,
                    "deal_closed": rt.deal_closed,
                    "awaiting_reply": bs.awaiting_reply,
                    "turns": bs.turns,
                    "belief": {
                        "est_floor": bs.belief.est_floor,
                        "confidence": bs.belief.confidence,
                        "momentum": bs.belief.momentum,
                        "stalled_turns": bs.belief.stalled_turns,
                    },
                }
            )
        return {
            "id": self.id,
            "mode": self.mode,
            "phase": self.phase,
            "running": self.running,
            "paused": self.paused,
            "buyer": {
                "company": self.buyer.company,
                "seats": self.buyer.seats,
                "budget_per_seat": self.buyer.budget_per_seat,
                "priorities": self.buyer.priorities,
            },
            "strategy": {
                "tactic": self.strategy.tactic,
                "rationale": self.strategy.rationale,
                "target_vendor_id": self.strategy.target_vendor_id,
                "target_price": self.strategy.target_price,
                "source": self.strategy.source,
            },
            "agents": agents,
            "threads": self.mailbox.thread_snapshot(),
            "logs": [l.model_dump() for l in self.logs[-200:]],
            "research": [r.model_dump() for r in self.research],
            "contract": self.contract.model_dump() if self.contract else None,
            "winner_id": self.winner_id,
            "summary": self.summary,
        }
