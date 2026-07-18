"""In-memory store of live negotiation runtimes (single-process demo)."""
from __future__ import annotations

from .orchestrator import NegotiationRuntime

_RUNTIMES: dict[str, NegotiationRuntime] = {}


def save(rt: NegotiationRuntime) -> None:
    _RUNTIMES[rt.id] = rt


def get(neg_id: str) -> NegotiationRuntime | None:
    return _RUNTIMES.get(neg_id)


def delete(neg_id: str) -> None:
    _RUNTIMES.pop(neg_id, None)
