"""Thin OpenAI helper. Optional: when no key is present the agents fall back to
their deterministic mock drafting so the whole demo runs offline.
"""
from __future__ import annotations

import json
import os

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def use_llm() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and os.getenv("USE_MOCK") != "1"


def _client():
    from openai import AsyncOpenAI

    return AsyncOpenAI()


async def json_call(system: str, user: str, temperature: float = 0.8) -> dict:
    """Ask the model for a JSON object. Returns {} on any failure so callers can
    gracefully fall back to their mock path."""
    try:
        client = _client()
        resp = await client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return {}
