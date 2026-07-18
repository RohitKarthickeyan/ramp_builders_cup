import { useNegotiation } from "../ws";
import AgentRoster from "./AgentRoster";
import Inbox from "./Inbox";
import ActivityFeed from "./ActivityFeed";
import ResearchPanel from "./ResearchPanel";
import CoachBar from "./CoachBar";
import DealChart from "./DealChart";
import ContractModal from "./ContractModal";

const PHASE_LABEL: Record<string, string> = {
  idle: "Ready",
  negotiating: "Negotiating",
  awaiting_approval: "Awaiting approval",
  done: "Done",
};

export default function Dashboard({
  negId,
  onReset,
}: {
  negId: string;
  onReset: () => void;
}) {
  const { state, connected, send } = useNegotiation(negId);

  if (!state) {
    return <div className="muted" style={{ padding: 40 }}>Connecting to negotiation…</div>;
  }

  const showContract = !!state.contract;

  return (
    <div className="dash">
      <div className="dash-bar">
        <div className="dash-status">
          <span className={"conn-dot" + (connected ? " on" : "")} />
          <strong>{PHASE_LABEL[state.phase]}</strong>
          {state.paused && <span className="pill-warn">paused</span>}
          <span className="muted small">
            {state.buyer.company} · {state.buyer.seats} seats · target ${state.buyer.budget_per_seat}/seat
          </span>
        </div>
        <button className="ghost small-btn" onClick={onReset}>New negotiation</button>
      </div>

      <div className="dash-grid">
        <div className="dash-left">
          <AgentRoster state={state} />
          <DealChart state={state} />
        </div>

        <div className="dash-center">
          <Inbox state={state} />
        </div>

        <div className="dash-right">
          <CoachBar state={state} send={send} />
          <ActivityFeed logs={state.logs} />
          <ResearchPanel state={state} />
        </div>
      </div>

      {showContract && (
        <ContractModal
          contract={state.contract!}
          phase={state.phase}
          summary={state.summary}
          send={send}
          onReset={onReset}
        />
      )}
    </div>
  );
}
