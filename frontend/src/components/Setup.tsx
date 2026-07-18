import { useState } from "react";
import type { BuyerConfig } from "../types";

const ALL_PRIORITIES = [
  "lowest price",
  "flexible contract length",
  "premium support",
  "free seats",
];

export default function Setup({ onStart }: { onStart: (b: BuyerConfig) => void }) {
  const [company, setCompany] = useState("Ramp");
  const [seats, setSeats] = useState(200);
  const [budget, setBudget] = useState(28);
  const [priorities, setPriorities] = useState<string[]>([
    "lowest price",
    "flexible contract length",
  ]);

  function toggle(p: string) {
    setPriorities((cur) =>
      cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]
    );
  }

  return (
    <div className="setup">
      <div className="setup-card">
        <h2>New negotiation</h2>
        <p className="muted small">
          Your AI procurement agent will email Cursor, Claude Code and Codex in
          parallel, negotiate a corporate discount autonomously, and draft a
          contract for your approval. Coach it live as it works.
        </p>

        <span className="field-label">Buyer</span>
        <div className="row">
          <div className="field">
            <input value={company} onChange={(e) => setCompany(e.target.value)} />
            <span className="muted small">Company</span>
          </div>
          <div className="field">
            <input
              type="number"
              value={seats}
              onChange={(e) => setSeats(+e.target.value)}
            />
            <span className="muted small">Seats</span>
          </div>
          <div className="field">
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(+e.target.value)}
            />
            <span className="muted small">Target $/seat/mo</span>
          </div>
        </div>

        <span className="field-label">Priorities</span>
        <div className="chips">
          {ALL_PRIORITIES.map((p) => (
            <button
              key={p}
              className={"chip" + (priorities.includes(p) ? " on" : "")}
              onClick={() => toggle(p)}
            >
              {p}
            </button>
          ))}
        </div>

        <button
          className="primary big"
          onClick={() =>
            onStart({ company, seats, budget_per_seat: budget, priorities })
          }
        >
          Create negotiation →
        </button>
      </div>

      <div className="vendor-preview">
        <h3>The field</h3>
        <div className="vp-row" style={{ borderColor: "#7c5cff" }}>
          <div className="vp-dot" style={{ background: "#7c5cff" }} />
          <div>
            <strong>Cursor</strong>
            <p className="muted small">Scrappy challenger — discounts hard, replies fast.</p>
          </div>
        </div>
        <div className="vp-row" style={{ borderColor: "#d4a27f" }}>
          <div className="vp-dot" style={{ background: "#d4a27f" }} />
          <div>
            <strong>Claude Code</strong>
            <p className="muted small">Premium & deliberate — holds price, slow to reply.</p>
          </div>
        </div>
        <div className="vp-row" style={{ borderColor: "#10a37f" }}>
          <div className="vp-dot" style={{ background: "#10a37f" }} />
          <div>
            <strong>Codex</strong>
            <p className="muted small">Incumbent — leans on ecosystem, variable timing.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
