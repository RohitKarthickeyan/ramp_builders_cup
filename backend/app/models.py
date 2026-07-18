"""Pydantic models shared across the negotiation engine and API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Deal terms
# ---------------------------------------------------------------------------
class Offer(BaseModel):
    """A concrete, multi-issue offer for a SaaS contract."""

    price_per_seat: float = Field(..., description="Monthly price per seat, USD")
    contract_length_months: int = Field(12, description="Committed contract length")
    free_seats: int = Field(0, description="Bonus seats thrown in for free")
    support_tier: Literal["standard", "priority", "premium"] = "standard"

    def annual_total(self, seats: int) -> float:
        """Effective annual cost given a seat count (free seats reduce cost)."""
        billable = max(seats - self.free_seats, 0)
        return round(billable * self.price_per_seat * 12, 2)


# ---------------------------------------------------------------------------
# Vendor definition (hidden state lives here)
# ---------------------------------------------------------------------------
class Vendor(BaseModel):
    id: str
    name: str
    tagline: str
    persona: str  # short description that flavors the agent's voice
    color: str  # UI accent

    list_price_per_seat: float  # public anchor
    target_price_per_seat: float  # what they'd love to close at (hidden)
    floor_price_per_seat: float  # walk-away price, never cross (hidden)
    competitiveness: float = Field(
        0.5, ge=0, le=1, description="How hard they cave under competitive pressure"
    )

    def public_view(self) -> dict:
        """Only the info the buyer/UI is allowed to see up front."""
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "persona": self.persona,
            "color": self.color,
            "list_price_per_seat": self.list_price_per_seat,
        }


# ---------------------------------------------------------------------------
# Buyer requirements / priorities
# ---------------------------------------------------------------------------
class BuyerConfig(BaseModel):
    seats: int = 50
    budget_per_seat: float = 30.0  # target monthly price per seat
    priorities: list[str] = Field(
        default_factory=lambda: ["lowest price", "flexible contract length"]
    )
    must_haves: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Transcript / turns
# ---------------------------------------------------------------------------
class Message(BaseModel):
    speaker: Literal["buyer", "vendor"]
    text: str
    reasoning: Optional[str] = None  # private thinking, shown to spectator
    offer: Optional[Offer] = None
    round: int = 0
    walk_away: bool = False


class VendorState(BaseModel):
    vendor: Vendor
    messages: list[Message] = Field(default_factory=list)
    current_offer: Optional[Offer] = None
    walked_away: bool = False
    deal_closed: bool = False

    def price_history(self) -> list[Optional[float]]:
        history: list[Optional[float]] = [self.vendor.list_price_per_seat]
        for m in self.messages:
            if m.speaker == "vendor" and m.offer is not None:
                history.append(m.offer.price_per_seat)
        return history


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
class Negotiation(BaseModel):
    id: str
    category: str
    buyer: BuyerConfig
    vendors: dict[str, VendorState]
    round: int = 0
    max_rounds: int = 6
    finished: bool = False
    winner_id: Optional[str] = None

    def public_dict(self) -> dict:
        """Serialize for the frontend (hidden vendor numbers stripped)."""
        return {
            "id": self.id,
            "category": self.category,
            "buyer": self.buyer.model_dump(),
            "round": self.round,
            "max_rounds": self.max_rounds,
            "finished": self.finished,
            "winner_id": self.winner_id,
            "vendors": [
                {
                    **vs.vendor.public_view(),
                    "messages": [m.model_dump() for m in vs.messages],
                    "current_offer": vs.current_offer.model_dump()
                    if vs.current_offer
                    else None,
                    "walked_away": vs.walked_away,
                    "deal_closed": vs.deal_closed,
                    "price_history": vs.price_history(),
                    "annual_total": vs.current_offer.annual_total(self.buyer.seats)
                    if vs.current_offer
                    else None,
                    "list_annual_total": round(
                        vs.vendor.list_price_per_seat * self.buyer.seats * 12, 2
                    ),
                }
                for vs in self.vendors.values()
            ],
        }


# ---------------------------------------------------------------------------
# API request bodies
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    category_id: str = "coding"
    buyer: Optional[BuyerConfig] = None


class RoundRequest(BaseModel):
    strategy: Optional[str] = None  # free-text or card label injected by the human
    target_vendor_id: Optional[str] = None  # for strategies aimed at one vendor
    close_vendor_id: Optional[str] = None  # human accepts a vendor's current offer
