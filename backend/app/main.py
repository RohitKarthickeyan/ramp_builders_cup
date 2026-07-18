"""FastAPI app: create a negotiation, then drive & monitor it live over a
WebSocket. All agent activity, emails, research, strategy and the final
contract stream to the dashboard; coaching and controls flow back."""
from __future__ import annotations

import asyncio
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import llm, store
from .models import StartRequest
from .orchestrator import NegotiationRuntime
from .scenarios import categories_public, get_category

load_dotenv()

app = FastAPI(title="Leverage — Live Negotiation Ops")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "mode": "llm" if llm.use_llm() else "mock", "model": llm.MODEL}


@app.get("/api/categories")
def get_categories():
    return {"categories": categories_public()}


@app.post("/api/negotiations")
def create_negotiation(req: StartRequest):
    try:
        cat = get_category(req.category_id)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    from .models import BuyerConfig

    buyer = req.buyer or BuyerConfig()
    vendors = [v.model_copy(deep=True) for v in cat["vendors"]]
    rt = NegotiationRuntime(
        neg_id=uuid.uuid4().hex[:12],
        buyer=buyer,
        vendors=vendors,
        mode="llm" if llm.use_llm() else "mock",
    )
    store.save(rt)
    return {"id": rt.id, "state": rt.snapshot()}


@app.get("/api/negotiations/{neg_id}")
def get_negotiation(neg_id: str):
    rt = store.get(neg_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return {"id": rt.id, "state": rt.snapshot()}


async def _handle_client_message(rt: NegotiationRuntime, msg: dict):
    kind = msg.get("type")
    if kind == "start":
        rt.start()
        await rt.broadcast()
    elif kind == "coach":
        text = (msg.get("text") or "").strip()
        if text:
            await rt.apply_coaching(text)
    elif kind == "pause":
        await rt.pause()
    elif kind == "resume":
        await rt.resume()
    elif kind == "stop":
        await rt.stop()
    elif kind == "approve_contract":
        await rt.approve_contract()
    elif kind == "reject_contract":
        await rt.reject_contract((msg.get("note") or "").strip())


@app.websocket("/api/negotiations/{neg_id}/ws")
async def negotiation_ws(websocket: WebSocket, neg_id: str):
    rt = store.get(neg_id)
    if not rt:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    queue = rt.subscribe()
    await websocket.send_json({"type": "state", "state": rt.snapshot()})

    async def pump_out():
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)

    async def pump_in():
        while True:
            msg = await websocket.receive_json()
            await _handle_client_message(rt, msg)

    out_task = asyncio.create_task(pump_out())
    in_task = asyncio.create_task(pump_in())
    try:
        await asyncio.wait({out_task, in_task}, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        out_task.cancel()
        in_task.cancel()
        rt.unsubscribe(queue)
