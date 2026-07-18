import type { Agent, NegState } from "../types";

const STATUS_COLOR: Record<string, string> = {
  idle: "#8a8aa0",
  reading: "#ffcf5a",
  drafting: "#ffcf5a",
  researching: "#7c5cff",
  waiting: "#5a9adf",
  sent: "#5ad19a",
  blocked: "#ff6b6b",
  done: "#5ad19a",
};

function BeliefBar({ agent }: { agent: Agent }) {
  const list = agent.list_price_per_seat ?? 0;
  const offer = agent.current_offer?.price_per_seat ?? list;
  const floor = agent.belief?.est_floor ?? offer;
  // Scale between est_floor and list price.
  const span = Math.max(list - floor, 1);
  const offerPct = Math.max(0, Math.min(100, ((list - offer) / span) * 100));
  return (
    <div className="belief">
      <div className="belief-row">
        <span className="muted small">est. floor ${floor.toFixed(2)}</span>
        <span className="muted small">list ${list.toFixed(0)}</span>
      </div>
      <div className="belief-track">
        <div className="belief-fill" style={{ width: `${offerPct}%`, background: agent.color }} />
        <div className="belief-marker" style={{ left: `${offerPct}%` }} title={`offer $${offer.toFixed(2)}`} />
      </div>
      <div className="belief-row">
        <span className="small" style={{ color: agent.color }}>now ${offer.toFixed(2)}</span>
        <span className="muted small">conf {Math.round((agent.belief?.confidence ?? 0) * 100)}%</span>
      </div>
    </div>
  );
}

function Card({ agent, winner }: { agent: Agent; winner: boolean }) {
  const dot = STATUS_COLOR[agent.status] ?? "#8a8aa0";
  const cls = "agent-card" + (agent.walked_away ? " walked" : "") + (winner ? " winner" : "");
  return (
    <div className={cls} style={{ borderTopColor: agent.color }}>
      <div className="agent-head">
        <div className="th-title">
          <span className="th-dot" style={{ background: dot, boxShadow: `0 0 8px ${dot}` }} />
          <strong>{agent.name}</strong>
        </div>
        {agent.kind === "vendor" && agent.current_offer && (
          <span className="agent-price" style={{ color: agent.color }}>
            ${agent.current_offer.price_per_seat.toFixed(2)}
          </span>
        )}
      </div>
      <div className="agent-status">
        <span className="status-tag">{agent.status}</span>
        <span className="muted small">{agent.activity}</span>
      </div>
      {agent.kind === "vendor" && <BeliefBar agent={agent} />}
      {agent.kind === "vendor" && agent.current_offer && (
        <div className="agent-terms muted small">
          {agent.current_offer.contract_length_months}mo · {agent.current_offer.free_seats} free ·{" "}
          {agent.current_offer.support_tier} · {agent.turns ?? 0} rounds
        </div>
      )}
    </div>
  );
}

export default function AgentRoster({ state }: { state: NegState }) {
  const buyer = state.agents.find((a) => a.kind === "buyer");
  const vendors = state.agents.filter((a) => a.kind === "vendor");
  return (
    <div className="roster">
      {buyer && <Card agent={buyer} winner={false} />}
      <div className="roster-label muted small">Vendors ({vendors.length})</div>
      {vendors.map((v) => (
        <Card key={v.id} agent={v} winner={state.winner_id === v.id} />
      ))}
    </div>
  );
}
