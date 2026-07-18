"""Trivial in-memory session store. Fine for a single-process hackathon demo."""
from __future__ import annotations

from .models import Negotiation

_SESSIONS: dict[str, Negotiation] = {}


def save(neg: Negotiation) -> None:
    _SESSIONS[neg.id] = neg


def get(neg_id: str) -> Negotiation | None:
    return _SESSIONS.get(neg_id)


def delete(neg_id: str) -> None:
    _SESSIONS.pop(neg_id, None)
