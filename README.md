# Leverage — Autonomous Contract Negotiation, Monitored Live

An **agent-operations dashboard**. Your AI **procurement agent** negotiates a
corporate SaaS discount with three **vendor agents** (Cursor, Claude Code,
Codex) entirely over a **simulated inbox** — drafting and sending emails,
running online research, following up on slow vendors, and adapting its strategy
when you coach it. You watch it all happen live and approve the final contract.

> Not a chat loop. The agents run autonomously and asynchronously; you *monitor
> and coach*, you don't type each message.

## What makes it tick

- **Simulated email bus** (`mailbox.py`) — the only channel between agents. No
  real Gmail; a fully in-memory inbox with per-vendor threads.
- **Autonomous agents on their own async tasks** (`buyer_agent.py`,
  `vendor_agent.py`) — vendors reply after a **variable, personality-driven
  delay**, so the buyer sometimes has to **follow up** (timing is randomized).
- **A strategy brain** — the buyer runs an OODA loop: *observe* new emails →
  *orient* by updating a **belief model** of each vendor's hidden floor →
  *decide* a tactic (anchor, cross-leverage, bluff, deadline, squeeze extras,
  hold, walk) → *act* by drafting an email. Beliefs and tactics stream to the UI.
- **Live coaching injection** — drop a strategy in at any moment over the
  WebSocket; the agent adopts the new tactic on its next move.
- **Online research** (`research.py`) — the agent pulls peer contract
  benchmarks and discount codes and quotes them as leverage. (Curated/simulated
  for a reliable demo; swap in a real search backend behind the same interface.)
- **Contract on close** (`contract.py`) — once the field converges the agent
  drafts a structured contract; a human **approves, or sends it back** to
  renegotiate.
- **Everything streams over one WebSocket** (`orchestrator.py` → `main.py`):
  agent statuses, emails, reasoning, research, strategy, and the contract.

Runs fully offline in **mock mode** (deterministic agents) or with real
**OpenAI**-drafted emails when `OPENAI_API_KEY` is set.

## Run it

```bash
./run.sh
# Backend  → http://localhost:8787
# Frontend → http://localhost:5173
```

Open the frontend, create a negotiation, hit **Start**, and coach away.

## Architecture

```
backend/app/
  models.py        Email, Belief, Strategy, Contract, ...
  mailbox.py       Simulated inbox (threads + read pointers)
  vendor_agent.py  Vendor sales agents (variable-latency email replies, hidden floor)
  buyer_agent.py   Procurement agent — the OODA strategy brain
  research.py      Discount codes + comparable-contract benchmarks (tool)
  engine.py        Buyer-utility scoring (lowest real annual cost wins)
  contract.py      Draft contract from the winning offer
  orchestrator.py  Concurrent agent tasks, event bus, coaching, pause/stop/approve
  main.py          FastAPI: create negotiation + live WebSocket

frontend/src/
  ws.ts            WebSocket hook (state in, coaching/controls out)
  components/
    Dashboard.tsx    Layout
    AgentRoster.tsx  Agent status + belief bars
    Inbox.tsx        Live threaded email view
    ActivityFeed.tsx Streaming agent reasoning/actions
    CoachBar.tsx     Live coaching + controls + current tactic
    ResearchPanel.tsx Benchmarks & discount codes
    DealChart.tsx    Price convergence vs target
    ContractModal.tsx Approve / renegotiate
```

## WebSocket protocol

Client → server: `start`, `coach {text}`, `pause`, `resume`, `stop`,
`approve_contract`, `reject_contract {note}`.
Server → client: `{type:"state", state}` — a full authoritative snapshot after
every meaningful step (agents, threads, logs, research, strategy, contract).
