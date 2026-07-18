import { useEffect, useState } from "react";
import { api } from "./api";
import type { BuyerConfig } from "./types";
import Setup from "./components/Setup";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [mode, setMode] = useState<string>("");
  const [negId, setNegId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("offline"));
  }, []);

  async function handleStart(buyer: BuyerConfig) {
    try {
      const { id } = await api.create(buyer);
      setNegId(id);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">⚖️</span>
          <div>
            <h1>Leverage</h1>
            <p>Autonomous contract negotiation — live agent ops</p>
          </div>
        </div>
        <div className="mode-pill" data-mode={mode}>
          {mode === "llm" ? "● Live AI" : mode === "mock" ? "● Simulated agents" : "○ …"}
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      {!negId ? (
        <Setup onStart={handleStart} />
      ) : (
        <Dashboard negId={negId} onReset={() => setNegId(null)} />
      )}
    </div>
  );
}
