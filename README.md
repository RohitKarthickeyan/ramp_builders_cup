# Leverage — Multi-Vendor Negotiation Game

A human-in-the-loop negotiation simulator for the **save time / money** track.

You're buying a SaaS tool (AI coding assistant, or team chat) and you're
**vendor-agnostic**. Your AI procurement agent negotiates with all three vendors
**at once**, and you coach it with strategies — start a bidding war, bluff about a
competitor, create urgency, squeeze non-price extras, hold firm, or walk away.
Watch each agent's private reasoning, see prices converge on a live chart, then
close with whoever gives you the best deal and see the **dollars saved**.

Under the game is a real product: automated vendor negotiation that cuts SaaS spend.

## What's inside

- **3 vendor agents** per scenario, each with hidden state: a public list price, a
  private target, a hard **walk-away floor** (never crossed), a competitiveness
  dial, and a distinct persona (challenger vs. incumbent vs. volume giant).
- **Cross-leverage**: your buyer agent quotes the best competing offer to squeeze
  each vendor — the core mechanic that drives a real bidding war.
- **Strategy cards + free-text coaching** injected between rounds.
- **Visible private reasoning** per agent (toggle on/off) — turns a chat log into a
  spectator sport.
- **Live price-convergence chart** with your target line.
- **Utility-based scoring**: winner maximizes *your* value (price vs. budget,
  savings vs. list, non-price sweeteners, and your stated priorities), plus a
  headline **$/yr saved** number for judges.
- **Two backends**: real **OpenAI** agents when `OPENAI_API_KEY` is set, or a
  deterministic **mock** engine so the demo always runs offline.

## Scenarios

- **AI Coding Assistants** — Cursor · Claude Code · Codex
- **Team Chat** — Slack · Microsoft Teams · Google Chat

Add more in `backend/app/scenarios.py`.

## Run it

```bash
./run.sh
```

Then open http://localhost:5173. That starts the FastAPI backend on `:8787` and
the Vite frontend on `:5173`.

### Enable real AI agents (optional)

```bash
cd backend
cp .env.example .env      # add your OPENAI_API_KEY
```

Without a key it runs in **mock mode** (shown as a pill in the top-right). Set
`USE_MOCK=1` to force mock mode even with a key.

### Manual start

```bash
# backend
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8787 --reload

# frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Architecture

```
backend/app/
  models.py      pydantic models (Offer, Vendor, Negotiation, ...)
  scenarios.py   vendor presets with hidden target/floor pricing
  agents.py      buyer + vendor turns (OpenAI mode + mock mode)
  engine.py      setup, utility scoring, winner selection, scorecard
  main.py        FastAPI routes
  store.py       in-memory session store

frontend/src/
  components/    Setup, Arena, VendorThread, StrategyBar, PriceChart, Scorecard
  api.ts         typed API client
```

### API

| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/health` | mode (llm/mock) + model |
| GET  | `/api/categories` | scenarios for the setup screen |
| POST | `/api/negotiations` | start a negotiation |
| GET  | `/api/negotiations/{id}` | fetch state |
| POST | `/api/negotiations/{id}/round` | advance a round (with optional `strategy`, `target_vendor_id`, or `close_vendor_id`) |
| POST | `/api/negotiations/{id}/finish` | close and score |

## Ideas to extend

- Voice mode (agents negotiate out loud) for a live audience.
- Vendors that *know* they're competing and reference rivals by name.
- Real invoice/renewal import → draft the actual negotiation email.
- Tournament / leaderboard for who coaches the best negotiator.
- Deadline pressure that accelerates concessions near the final round.
