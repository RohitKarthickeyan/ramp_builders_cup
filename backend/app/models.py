"""Pydantic models for the live, email-based negotiation ops dashboard.

The system simulates an *inbox*: a buyer (procurement) agent and several vendor
agents exchange emails. Agents draft and send messages asynchronously with
variable latency, the buyer may follow up, and a human can inject coaching at
any time. The end goal is a drafted contract a human can approve.
"""
from __future__ import annotations

import time
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# Deal terms
# ---------------------------------------------------------------------------
class Offer(BaseModel):
    """A concrete, multi-issue offer for a SaaS contract."""

    price_per_seat: float = Field(..., description="Monthly price per seat, USD")
    contract_length_months: int = 12
    free_seats: int = 0
    support_tier: Literal["standard", "priority", "premium"] = "standard"
    notes: Optional[str] = None

    def annual_total(self, seats: int) -> float:
        billable = max(seats - self.free_seats, 0)
        return round(billable * self.price_per_seat * 12, 2)


# ---------------------------------------------------------------------------
# Vendor definition (hidden pricing state lives here)
# ---------------------------------------------------------------------------
class Vendor(BaseModel):
    id: str
    name: str
    tagline: str
    persona: str
    color: str

    list_price_per_seat: float  # public anchor
    target_price_per_seat: float  # what they'd love to close at (hidden)
    floor_price_per_seat: float  # walk-away price, never cross (hidden)
    competitiveness: float = Field(0.5, ge=0, le=1)

    # Variable-latency personality: min/max seconds before an email reply.
    reply_min_s: float = 4.0
    reply_max_s: float = 14.0

    def public_view(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "persona": self.persona,
            "color": self.color,
            "list_price_per_seat": self.list_price_per_seat,
        }


# ---------------------------------------------------------------------------
# Buyer requirements
# ---------------------------------------------------------------------------
class BuyerConfig(BaseModel):
    company: str = "Ramp"
    seats: int = 200
    budget_per_seat: float = 28.0  # the "number we have in mind" (target)
    priorities: list[str] = Field(
        default_factory=lambda: ["lowest price", "flexible contract length"]
    )
    must_haves: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Email / inbox
# ---------------------------------------------------------------------------
class Email(BaseModel):
    id: str = Field(default_factory=lambda: _id("em_"))
    thread_id: str
    sender_id: str  # agent id ("buyer" or vendor id)
    sender_role: Literal["buyer", "vendor"]
    sender_name: str
    to_id: str
    to_name: str
    subject: str
    body: str
    ts: float = Field(default_factory=now)
    offer: Optional[Offer] = None
    is_followup: bool = False


class Thread(BaseModel):
    id: str
    vendor_id: str
    subject: str
    emails: list[Email] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Buyer's belief model about each vendor (the "strategy brain" state)
# ---------------------------------------------------------------------------
class Belief(BaseModel):
    vendor_id: str
    est_floor: float  # buyer's running estimate of the vendor's true floor
    confidence: float = 0.2  # 0..1, grows as the vendor reveals concessions
    momentum: float = 0.0  # $ moved on the vendor's last reply (positive = conceding)
    last_price: Optional[float] = None
    stalled_turns: int = 0  # consecutive replies with little/no movement


class ResearchFinding(BaseModel):
    source: str
    text: str
    url: Optional[str] = None
    price_per_seat: Optional[float] = None


class ResearchReport(BaseModel):
    id: str = Field(default_factory=lambda: _id("rs_"))
    vendor_id: str
    query: str
    findings: list[ResearchFinding] = Field(default_factory=list)
    ts: float = Field(default_factory=now)


# ---------------------------------------------------------------------------
# Strategy / coaching
# ---------------------------------------------------------------------------
Tactic = Literal[
    "anchor",
    "cross_leverage",
    "bluff",
    "deadline",
    "squeeze_non_price",
    "hold_firm",
    "walk_away",
]


class Strategy(BaseModel):
    tactic: Tactic = "anchor"
    rationale: str = "Open with an aggressive but credible anchor near our target."
    target_vendor_id: Optional[str] = None  # None = applies to all
    target_price: Optional[float] = None  # explicit $/seat the coach demanded, if any
    source: Literal["default", "coaching", "auto"] = "default"
    ts: float = Field(default_factory=now)


# ---------------------------------------------------------------------------
# Contract (the deliverable)
# ---------------------------------------------------------------------------
class Contract(BaseModel):
    id: str = Field(default_factory=lambda: _id("ct_"))
    vendor_id: str
    vendor_name: str
    buyer_company: str
    seats: int
    price_per_seat: float
    contract_length_months: int
    free_seats: int
    support_tier: str
    annual_total: float
    list_annual_total: float
    savings: float
    savings_pct: float
    effective_date: str
    clauses: list[str] = Field(default_factory=list)
    status: Literal["draft", "approved", "rejected"] = "draft"
    ts: float = Field(default_factory=now)


# ---------------------------------------------------------------------------
# Activity log entries (the reasoning feed)
# ---------------------------------------------------------------------------
LogKind = Literal["system", "reasoning", "strategy", "research", "email", "action", "coaching"]


class LogEntry(BaseModel):
    id: str = Field(default_factory=lambda: _id("lg_"))
    agent_id: str
    agent_name: str
    kind: LogKind
    text: str
    ts: float = Field(default_factory=now)


# ---------------------------------------------------------------------------
# API request bodies
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    category_id: str = "coding"
    buyer: Optional[BuyerConfig] = None
