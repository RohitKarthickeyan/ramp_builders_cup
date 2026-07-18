import { useEffect, useState } from "react";
import { api } from "../api";
import type { BuyerConfig, CategoryView } from "../types";

const PRIORITY_OPTIONS = [
  "lowest price",
  "flexible contract length",
  "long-term stability",
  "premium support",
];

export default function Setup({
  onStart,
}: {
  onStart: (categoryId: string, buyer: BuyerConfig) => Promise<void>;
}) {
  const [categories, setCategories] = useState<CategoryView[]>([]);
  const [categoryId, setCategoryId] = useState("coding");
  const [seats, setSeats] = useState(60);
  const [budget, setBudget] = useState(28);
  const [priorities, setPriorities] = useState<string[]>([
    "lowest price",
    "flexible contract length",
  ]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => {});
  }, []);

  const cat = categories.find((c) => c.id === categoryId);

  function togglePriority(p: string) {
    setPriorities((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  async function go() {
    setBusy(true);
    try {
      await onStart(categoryId, {
        seats,
        budget_per_seat: budget,
        priorities,
        must_haves: [],
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="setup">
      <div className="setup-card">
        <h2>Set up the deal</h2>
        <p className="muted">
          You're vendor-agnostic. Negotiate all three at once and play them against
          each other to drive the price down.
        </p>

        <label className="field-label">What are you buying?</label>
        <div className="cat-grid">
          {categories.map((c) => (
            <button
              key={c.id}
              className={`cat-tile ${c.id === categoryId ? "active" : ""}`}
              onClick={() => setCategoryId(c.id)}
            >
              <strong>{c.label}</strong>
              <span className="muted">{c.vendors.map((v) => v.name).join(" · ")}</span>
            </button>
          ))}
        </div>

        <div className="row">
          <div className="field">
            <label className="field-label">Seats</label>
            <input
              type="number"
              min={1}
              value={seats}
              onChange={(e) => setSeats(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label className="field-label">Target $/seat/mo</label>
            <input
              type="number"
              min={1}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
            />
          </div>
        </div>

        <label className="field-label">Priorities</label>
        <div className="chips">
          {PRIORITY_OPTIONS.map((p) => (
            <button
              key={p}
              className={`chip ${priorities.includes(p) ? "on" : ""}`}
              onClick={() => togglePriority(p)}
            >
              {p}
            </button>
          ))}
        </div>

        <button className="primary big" disabled={busy} onClick={go}>
          {busy ? "Setting up…" : "Enter the negotiation →"}
        </button>
      </div>

      {cat && (
        <div className="vendor-preview">
          <h3>Your vendors</h3>
          {cat.vendors.map((v) => (
            <div key={v.id} className="vp-row" style={{ borderColor: v.color }}>
              <div className="vp-dot" style={{ background: v.color }} />
              <div>
                <strong>{v.name}</strong> <span className="muted">— {v.tagline}</span>
                <p className="muted small">{v.persona}</p>
              </div>
              <div className="vp-price">${v.list_price_per_seat}/seat list</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
