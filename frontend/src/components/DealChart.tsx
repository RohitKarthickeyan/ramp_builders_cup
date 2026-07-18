import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { NegState } from "../types";

export default function DealChart({ state }: { state: NegState }) {
  const vendors = state.agents.filter((a) => a.kind === "vendor");
  const maxLen = Math.max(...vendors.map((v) => v.price_history?.length ?? 0), 1);
  const data = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, number | string | null> = { step: i === 0 ? "list" : `#${i}` };
    for (const v of vendors) row[v.name] = v.price_history?.[i] ?? null;
    return row;
  });

  return (
    <div className="chart-card">
      <div className="chart-head">
        <h3>Price convergence</h3>
        <span className="muted small">$/seat/mo</span>
      </div>
      <ResponsiveContainer width="100%" height={190}>
        <LineChart data={data} margin={{ top: 8, right: 14, left: -14, bottom: 0 }}>
          <CartesianGrid stroke="#2a2a3a" strokeDasharray="3 3" />
          <XAxis dataKey="step" stroke="#8a8aa0" fontSize={11} />
          <YAxis stroke="#8a8aa0" fontSize={11} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              background: "#161622",
              border: "1px solid #2a2a3a",
              borderRadius: 8,
              color: "#e8e8f0",
              fontSize: 12,
            }}
          />
          <ReferenceLine
            y={state.buyer.budget_per_seat}
            stroke="#5ad19a"
            strokeDasharray="5 4"
            label={{ value: "target", fill: "#5ad19a", fontSize: 10, position: "insideTopLeft" }}
          />
          {vendors.map((v) => (
            <Line
              key={v.id}
              type="monotone"
              dataKey={v.name}
              stroke={v.color}
              strokeWidth={2.5}
              dot={{ r: 2.5 }}
              connectNulls
              isAnimationActive
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
