import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import type { Negotiation } from "../types";

export default function PriceChart({ neg }: { neg: Negotiation }) {
  const maxLen = Math.max(...neg.vendors.map((v) => v.price_history.length), 1);
  const data = Array.from({ length: maxLen }, (_, round) => {
    const row: Record<string, number | string | null> = {
      round: round === 0 ? "list" : `R${round}`,
    };
    for (const v of neg.vendors) {
      row[v.name] = v.price_history[round] ?? null;
    }
    return row;
  });

  return (
    <div className="chart-card">
      <div className="chart-head">
        <h3>Price convergence</h3>
        <span className="muted small">$/seat/month over rounds</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#2a2a3a" strokeDasharray="3 3" />
          <XAxis dataKey="round" stroke="#8a8aa0" fontSize={12} />
          <YAxis stroke="#8a8aa0" fontSize={12} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              background: "#161622",
              border: "1px solid #2a2a3a",
              borderRadius: 8,
              color: "#e8e8f0",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine
            y={neg.buyer.budget_per_seat}
            stroke="#5ad19a"
            strokeDasharray="5 4"
            label={{ value: "your target", fill: "#5ad19a", fontSize: 11, position: "insideTopLeft" }}
          />
          {neg.vendors.map((v) => (
            <Line
              key={v.id}
              type="monotone"
              dataKey={v.name}
              stroke={v.color}
              strokeWidth={2.5}
              dot={{ r: 3 }}
              connectNulls
              isAnimationActive
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
