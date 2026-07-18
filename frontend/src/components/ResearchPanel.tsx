import type { NegState } from "../types";

export default function ResearchPanel({ state }: { state: NegState }) {
  const reports = state.research;
  const nameOf = (vid: string) => state.agents.find((a) => a.id === vid)?.name ?? vid;

  return (
    <div className="research-card">
      <div className="chart-head">
        <h3>Market research</h3>
        <span className="muted small">{reports.length} reports</span>
      </div>
      {reports.length === 0 && (
        <div className="muted small">
          The agent runs online research (peer benchmarks & discount codes) as it negotiates.
        </div>
      )}
      <div className="research-list">
        {reports.map((r) => (
          <div key={r.id} className="research-report">
            <div className="research-q">
              <span className="research-badge">{nameOf(r.vendor_id)}</span> {r.query}
            </div>
            {r.findings.map((f, i) => (
              <div key={i} className="finding">
                <div className="finding-head">
                  {f.url ? (
                    <a href={f.url} target="_blank" rel="noreferrer" className="finding-src">
                      {f.source}
                    </a>
                  ) : (
                    <span className="finding-src">{f.source}</span>
                  )}
                  {f.price_per_seat != null && (
                    <span className="finding-price">${f.price_per_seat.toFixed(2)}/seat</span>
                  )}
                </div>
                <div className="muted small">{f.text}</div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
