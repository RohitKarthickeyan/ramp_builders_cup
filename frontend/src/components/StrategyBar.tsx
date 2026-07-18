import { useState } from "react";
import type { VendorView } from "../types";

export interface StrategyCard {
  id: string;
  label: string;
  emoji: string;
  prompt: string;
  targeted?: boolean; // needs a specific vendor
  hint: string;
}

export const CARDS: StrategyCard[] = [
  {
    id: "bidding_war",
    label: "Bidding War",
    emoji: "🔥",
    prompt: "Play them aggressively against each other and start a bidding war this round.",
    hint: "Force everyone to undercut the current best price.",
  },
  {
    id: "bluff",
    label: "Bluff",
    emoji: "🎭",
    prompt: "Bluff that a competitor has offered a dramatically lower price.",
    hint: "Claim a competing quote that may not exist.",
  },
  {
    id: "urgency",
    label: "Create Urgency",
    emoji: "⏰",
    prompt: "Create urgency — we sign by Friday or we walk. Push for their best number now.",
    hint: "A deadline squeezes out extra concessions.",
  },
  {
    id: "non_price",
    label: "Squeeze Extras",
    emoji: "🎁",
    prompt:
      "If the price is firm, squeeze non-price value: free seats, longer term for a bigger discount, premium support.",
    hint: "Win on total value when price stalls.",
  },
  {
    id: "hold",
    label: "Hold Firm",
    emoji: "🧊",
    prompt: "Hold firm on our target number and concede very slowly.",
    hint: "Signal discipline; make them move first.",
  },
  {
    id: "walk",
    label: "Walk Away",
    emoji: "🚪",
    prompt: "Threaten to walk away entirely unless they beat the best offer on the table.",
    targeted: true,
    hint: "Aim at one vendor to pressure the rest.",
  },
];

export default function StrategyBar({
  vendors,
  busy,
  round,
  maxRounds,
  onPlay,
  onFreeText,
}: {
  vendors: VendorView[];
  busy: boolean;
  round: number;
  maxRounds: number;
  onPlay: (card: StrategyCard, targetVendorId?: string) => void;
  onFreeText: (text: string) => void;
}) {
  const [target, setTarget] = useState<string>(vendors[0]?.id ?? "");
  const [text, setText] = useState("");

  return (
    <div className="strategy-bar">
      <div className="strategy-head">
        <h3>Coach your negotiator</h3>
        <span className="muted small">
          Round {round} / {maxRounds}
        </span>
      </div>

      <div className="cards">
        {CARDS.map((c) => (
          <button
            key={c.id}
            className="strat-card"
            disabled={busy}
            title={c.hint}
            onClick={() => onPlay(c, c.targeted ? target : undefined)}
          >
            <span className="emoji">{c.emoji}</span>
            <span className="label">{c.label}</span>
            <span className="hint">{c.hint}</span>
          </button>
        ))}
      </div>

      <div className="strategy-controls">
        <div className="target-select">
          <label className="muted small">Target for aimed cards (🚪):</label>
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            {vendors.map((v) => (
              <option key={v.id} value={v.id} disabled={v.walked_away}>
                {v.name}
              </option>
            ))}
          </select>
        </div>

        <div className="freetext">
          <input
            placeholder="…or type your own instruction (e.g. 'ask Slack to match Teams on price')"
            value={text}
            disabled={busy}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && text.trim()) {
                onFreeText(text.trim());
                setText("");
              }
            }}
          />
          <button
            className="primary"
            disabled={busy || !text.trim()}
            onClick={() => {
              onFreeText(text.trim());
              setText("");
            }}
          >
            Send
          </button>
        </div>
      </div>

      <button
        className="ghost run-round"
        disabled={busy}
        onClick={() => onFreeText("")}
      >
        {busy ? "Negotiating…" : "▶ Run round (no coaching)"}
      </button>
    </div>
  );
}
