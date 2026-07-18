import { useState } from "react";
import type { VendorView } from "../types";

export default function VendorThread({
  v,
  isBest,
  budget,
  onClose,
  finished,
}: {
  v: VendorView;
  isBest: boolean;
  budget: number;
  onClose: (id: string) => void;
  finished: boolean;
}) {
  const [showReasoning, setShowReasoning] = useState(true);
  const o = v.current_offer;

  return (
    <div
      className={`thread ${v.walked_away ? "walked" : ""} ${
        v.deal_closed ? "closed" : ""
      } ${isBest ? "best" : ""}`}
      style={{ ["--accent" as string]: v.color }}
    >
      <div className="thread-head">
        <div className="th-title">
          <span className="th-dot" style={{ background: v.color }} />
          <div>
            <strong>{v.name}</strong>
            <span className="muted small"> {v.tagline}</span>
          </div>
        </div>
        {isBest && !v.walked_away && <span className="badge">Best deal</span>}
        {v.walked_away && <span className="badge walked-badge">Walked away</span>}
      </div>

      <div className="offer-strip">
        <div className="offer-price">
          {o ? `$${o.price_per_seat.toFixed(2)}` : "—"}
          <span className="per">/seat</span>
        </div>
        <div className="offer-meta">
          <span className={o && o.price_per_seat <= budget ? "under" : "over"}>
            {o ? (o.price_per_seat <= budget ? "under budget" : "over budget") : ""}
          </span>
          {o && (
            <span className="muted small">
              {o.contract_length_months}mo · {o.free_seats} free · {o.support_tier}
            </span>
          )}
        </div>
      </div>

      <div className="reasoning-toggle">
        <label>
          <input
            type="checkbox"
            checked={showReasoning}
            onChange={(e) => setShowReasoning(e.target.checked)}
          />
          show private reasoning
        </label>
      </div>

      <div className="messages">
        {v.messages.length === 0 && (
          <p className="muted small empty">No messages yet — run a round.</p>
        )}
        {v.messages.map((m, i) => (
          <div key={i} className={`bubble ${m.speaker}`}>
            <div className="bubble-role">
              {m.speaker === "buyer" ? "You (via agent)" : v.name}
            </div>
            <div className="bubble-text">{m.text}</div>
            {showReasoning && m.reasoning && (
              <div className="bubble-reasoning">💭 {m.reasoning}</div>
            )}
          </div>
        ))}
      </div>

      {!finished && !v.walked_away && (
        <button className="accept" onClick={() => onClose(v.id)}>
          ✓ Accept {v.name}'s offer & close
        </button>
      )}
    </div>
  );
}
