import { useState } from "react";
import type { NegState } from "../types";
import type { OutMsg } from "../ws";

const QUICK = [
  { emoji: "🔥", label: "Bidding war", text: "Start a bidding war and play them against each other" },
  { emoji: "🎭", label: "Bluff", text: "Bluff that a competitor is being very aggressive on price" },
  { emoji: "⏰", label: "Deadline", text: "Set a hard Friday deadline for best-and-final offers" },
  { emoji: "🎁", label: "Squeeze extras", text: "Hold price and squeeze free seats and premium support" },
  { emoji: "🛡️", label: "Hold firm", text: "Hold firm on our target number" },
  { emoji: "🚪", label: "Walk away", text: "Threaten to walk away unless they hit our number" },
];

const TACTIC_LABEL: Record<string, string> = {
  anchor: "Anchor",
  cross_leverage: "Cross-leverage",
  bluff: "Bluff",
  deadline: "Deadline",
  squeeze_non_price: "Squeeze extras",
  hold_firm: "Hold firm",
  walk_away: "Walk away",
};

export default function CoachBar({
  state,
  send,
}: {
  state: NegState;
  send: (m: OutMsg) => void;
}) {
  const [text, setText] = useState("");
  const { phase, running, paused } = state;
  const started = phase !== "idle";
  const live = running && phase === "negotiating";

  return (
    <div className="coach-card">
      <div className="chart-head">
        <h3>Coach the agent</h3>
        <span className="strat-source" data-src={state.strategy.source}>
          {state.strategy.source}
        </span>
      </div>

      <div className="current-strat">
        <div className="strat-line">
          <span className="strat-tactic">{TACTIC_LABEL[state.strategy.tactic] ?? state.strategy.tactic}</span>
          {state.strategy.target_price != null && (
            <span className="strat-price">→ ${state.strategy.target_price.toFixed(2)}/seat</span>
          )}
          {state.strategy.target_vendor_id && (
            <span className="strat-target">
              @ {state.agents.find((a) => a.id === state.strategy.target_vendor_id)?.name}
            </span>
          )}
        </div>
        <span className="muted small">{state.strategy.rationale}</span>
      </div>

      <div className="controls">
        {!started && (
          <button className="primary" onClick={() => send({ type: "start" })}>
            ▶ Start negotiation
          </button>
        )}
        {started && phase === "negotiating" && !paused && (
          <button className="ghost" onClick={() => send({ type: "pause" })}>⏸ Pause</button>
        )}
        {started && paused && (
          <button className="primary" onClick={() => send({ type: "resume" })}>▶ Resume</button>
        )}
        {started && phase !== "done" && (
          <button className="ghost danger" onClick={() => send({ type: "stop" })}>⏹ Stop</button>
        )}
      </div>

      <div className="quick-cards">
        {QUICK.map((q) => (
          <button
            key={q.label}
            className="quick-card"
            disabled={!live}
            onClick={() => send({ type: "coach", text: q.text })}
            title={q.text}
          >
            <span className="emoji">{q.emoji}</span>
            <span className="label">{q.label}</span>
          </button>
        ))}
      </div>

      <div className="freetext">
        <input
          placeholder="Type a strategy… e.g. 'push Cursor harder'"
          value={text}
          disabled={!live}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && text.trim()) {
              send({ type: "coach", text: text.trim() });
              setText("");
            }
          }}
        />
        <button
          className="primary"
          disabled={!live || !text.trim()}
          onClick={() => {
            send({ type: "coach", text: text.trim() });
            setText("");
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
