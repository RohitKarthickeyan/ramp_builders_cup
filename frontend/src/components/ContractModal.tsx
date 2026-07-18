import { useState } from "react";
import type { Contract } from "../types";
import type { OutMsg } from "../ws";

export default function ContractModal({
  contract,
  phase,
  summary,
  send,
  onReset,
}: {
  contract: Contract;
  phase: string;
  summary: string | null;
  send: (m: OutMsg) => void;
  onReset: () => void;
}) {
  const [note, setNote] = useState("");
  const approved = contract.status === "approved" || phase === "done";

  return (
    <div className="scorecard-overlay">
      <div className="contract">
        <div className="contract-head">
          {approved ? <span className="trophy">✅</span> : <span className="trophy">📄</span>}
          <div>
            <h2>{approved ? "Contract signed" : "Draft contract — your approval needed"}</h2>
            <p className="muted small">
              {contract.buyer_company} × {contract.vendor_name} · effective {contract.effective_date}
            </p>
          </div>
        </div>

        <div className="contract-figures">
          <div>
            <div className="big-number">
              ${contract.price_per_seat.toFixed(2)}
              <span className="per">/seat/mo</span>
            </div>
            <span className="muted small">{contract.seats} seats · {contract.contract_length_months}mo · {contract.support_tier}</span>
          </div>
          <div>
            <div className="big-number" style={{ color: "#5ad19a" }}>
              ${contract.savings.toLocaleString()}
              <span className="per">/yr saved</span>
            </div>
            <span className="muted small">{contract.savings_pct}% under list · ${contract.annual_total.toLocaleString()}/yr</span>
          </div>
        </div>

        <div className="clauses">
          {contract.clauses.map((c, i) => (
            <div key={i} className="clause">• {c}</div>
          ))}
        </div>

        {approved ? (
          <div className="contract-actions">
            {summary && <p className="win-summary">{summary}</p>}
            <button className="ghost" onClick={onReset}>Start a new negotiation</button>
          </div>
        ) : (
          <div className="contract-actions">
            <div className="freetext">
              <input
                placeholder="Request changes (sent back as coaching)…"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <button className="ghost" onClick={() => send({ type: "reject_contract", note: note.trim() })}>
                ↩ Renegotiate
              </button>
            </div>
            <button className="primary big" onClick={() => send({ type: "approve_contract" })}>
              ✅ Approve & sign
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
