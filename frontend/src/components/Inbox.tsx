import { useEffect, useMemo, useRef, useState } from "react";
import type { Email, NegState } from "../types";

function fmtTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function EmailRow({ email, color }: { email: Email; color: string }) {
  const mine = email.sender_role === "buyer";
  return (
    <div className={"email " + (mine ? "from-buyer" : "from-vendor")}>
      <div className="email-head">
        <span className="email-from" style={{ color: mine ? "#7c5cff" : color }}>
          {email.sender_name}
        </span>
        {email.is_followup && <span className="followup-tag">follow-up</span>}
        <span className="muted small email-time">{fmtTime(email.ts)}</span>
      </div>
      <div className="email-body">{email.body}</div>
      {email.offer && (
        <div className="email-offer">
          <strong>${email.offer.price_per_seat.toFixed(2)}</strong>/seat ·{" "}
          {email.offer.contract_length_months}mo
          {email.offer.free_seats ? ` · ${email.offer.free_seats} free` : ""}
          {email.offer.support_tier !== "standard" ? ` · ${email.offer.support_tier}` : ""}
        </div>
      )}
    </div>
  );
}

export default function Inbox({ state }: { state: NegState }) {
  const threads = state.threads;
  const vendorColor = (vid: string) =>
    state.agents.find((a) => a.id === vid)?.color ?? "#8a8aa0";

  const [selected, setSelected] = useState<string | null>(null);
  const active = useMemo(() => {
    if (selected && threads.some((t) => t.id === selected)) return selected;
    // default: thread with the most recent email
    let best: string | null = null;
    let bestTs = -1;
    for (const t of threads) {
      const last = t.emails[t.emails.length - 1];
      if (last && last.ts > bestTs) {
        bestTs = last.ts;
        best = t.id;
      }
    }
    return best;
  }, [selected, threads]);

  const activeThread = threads.find((t) => t.id === active);
  const bodyRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [activeThread?.emails.length, active]);

  if (threads.length === 0) {
    return (
      <div className="inbox">
        <div className="inbox-empty muted">
          <p>📭 Inbox is empty.</p>
          <p className="small">Press <strong>Start</strong> to send the opening RFP.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="inbox">
      <div className="inbox-tabs">
        {threads.map((t) => {
          const last = t.emails[t.emails.length - 1];
          const c = vendorColor(t.vendor_id);
          return (
            <button
              key={t.id}
              className={"inbox-tab" + (t.id === active ? " active" : "")}
              onClick={() => setSelected(t.id)}
              style={t.id === active ? { borderColor: c } : {}}
            >
              <span className="th-dot" style={{ background: c }} />
              {state.agents.find((a) => a.id === t.vendor_id)?.name}
              <span className="tab-count">{t.emails.length}</span>
              {last && <span className="tab-preview muted small">{fmtTime(last.ts)}</span>}
            </button>
          );
        })}
      </div>
      <div className="inbox-subject muted small">{activeThread?.subject}</div>
      <div className="inbox-body" ref={bodyRef}>
        {activeThread?.emails.map((e) => (
          <EmailRow key={e.id} email={e} color={vendorColor(e.thread_id.replace("th_", ""))} />
        ))}
      </div>
    </div>
  );
}
