import type { Scorecard as ScorecardType } from "../types";

export default function Scorecard({
  sc,
  onReset,
}: {
  sc: ScorecardType;
  onReset: () => void;
}) {
  const winner = sc.winner;
  return (
    <div className="scorecard-overlay">
      <div className="scorecard">
        <span className="trophy">🏆</span>
        <h2>Deal closed with {winner?.name}</h2>
        {winner && (
          <div className="win-savings">
            <div className="big-number">
              ${winner.savings.toLocaleString()}
              <span className="per">/yr saved</span>
            </div>
            <div className="muted">
              {winner.savings_pct}% off list · ${winner.annual_total?.toLocaleString()} /yr
              at ${winner.final_price_per_seat}/seat
            </div>
          </div>
        )}

        <table className="score-table">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>$/seat</th>
              <th>Annual</th>
              <th>Saved</th>
              <th>Utility</th>
            </tr>
          </thead>
          <tbody>
            {sc.rows.map((r) => (
              <tr key={r.vendor_id} className={r.vendor_id === winner?.vendor_id ? "win" : ""}>
                <td>
                  {r.name}
                  {r.walked_away && <span className="muted small"> (walked)</span>}
                </td>
                <td>{r.final_price_per_seat != null ? `$${r.final_price_per_seat}` : "—"}</td>
                <td>{r.annual_total != null ? `$${r.annual_total.toLocaleString()}` : "—"}</td>
                <td className="pos">
                  {r.savings > 0 ? `$${r.savings.toLocaleString()} (${r.savings_pct}%)` : "—"}
                </td>
                <td>{r.score}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <button className="primary big" onClick={onReset}>
          New negotiation
        </button>
      </div>
    </div>
  );
}
