"""FastAPI app exposing the negotiation game."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import agents, engine, store
from .models import RoundRequest, StartRequest
from .scenarios import categories_public

load_dotenv()

app = FastAPI(title="Leverage — Multi-Vendor Negotiation Game")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mode": "llm" if (os.getenv("OPENAI_API_KEY") and os.getenv("USE_MOCK") != "1") else "mock",
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


@app.get("/api/categories")
def get_categories():
    return {"categories": categories_public()}


@app.post("/api/negotiations")
def create_negotiation(req: StartRequest):
    try:
        neg = engine.start_negotiation(req.category_id, req.buyer)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.save(neg)
    return neg.public_dict()


@app.get("/api/negotiations/{neg_id}")
def get_negotiation(neg_id: str):
    neg = store.get(neg_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return neg.public_dict()


@app.post("/api/negotiations/{neg_id}/round")
async def play_round(neg_id: str, req: RoundRequest):
    neg = store.get(neg_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    if neg.finished:
        raise HTTPException(status_code=400, detail="Negotiation already finished")

    # Human chooses to accept a vendor's current offer -> end the game.
    if req.close_vendor_id:
        engine.finish(neg, req.close_vendor_id)
        store.save(neg)
        return {"negotiation": neg.public_dict(), "scorecard": engine.scorecard(neg)}

    try:
        await agents.run_round(neg, req.strategy, req.target_vendor_id)
    except Exception as e:
        # Invalid/revoked key → fall back to mock so the demo still runs.
        from openai import AuthenticationError

        if isinstance(e, AuthenticationError):
            os.environ["USE_MOCK"] = "1"
            await agents.run_round(neg, req.strategy, req.target_vendor_id)
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Agent backend error ({type(e).__name__}): {str(e)[:180]}",
            )

    if neg.round >= neg.max_rounds:
        engine.finish(neg)

    store.save(neg)
    payload = {"negotiation": neg.public_dict(), "scorecard": None}
    if neg.finished:
        payload["scorecard"] = engine.scorecard(neg)
    return payload


@app.post("/api/negotiations/{neg_id}/finish")
def finish_negotiation(neg_id: str, req: RoundRequest):
    neg = store.get(neg_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    engine.finish(neg, req.close_vendor_id)
    store.save(neg)
    return {"negotiation": neg.public_dict(), "scorecard": engine.scorecard(neg)}
