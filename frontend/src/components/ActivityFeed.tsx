import { useEffect, useRef } from "react";
import type { LogEntry } from "../types";

const ICON: Record<string, string> = {
  reasoning: "🧠",
  strategy: "♟️",
  research: "🔎",
  email: "✉️",
  action: "⚡",
  coaching: "🎯",
  system: "⚙️",
};

function fmt(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function ActivityFeed({ logs }: { logs: LogEntry[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="feed-card">
      <div className="chart-head">
        <h3>Agent activity</h3>
        <span className="muted small">reasoning · actions</span>
      </div>
      <div className="feed" ref={ref}>
        {logs.length === 0 && <div className="muted small">No activity yet.</div>}
        {logs.map((l) => (
          <div key={l.id} className={"feed-row kind-" + l.kind}>
            <span className="feed-icon">{ICON[l.kind] ?? "•"}</span>
            <div className="feed-text">
              <div className="feed-meta">
                <span className="feed-agent">{l.agent_name}</span>
                <span className="muted small">{fmt(l.ts)}</span>
              </div>
              <div>{l.text}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
