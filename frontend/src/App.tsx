import { useEffect, useState } from "react";
import { api } from "./api";
import type { BuyerConfig, Negotiation, Scorecard } from "./types";
import Setup from "./components/Setup";
import Arena from "./components/Arena";

export default function App() {
  const [mode, setMode] = useState<string>("");
  const [neg, setNeg] = useState<Negotiation | null>(null);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("offline"));
  }, []);

  async function handleStart(categoryId: string, buyer: BuyerConfig) {
    const n = await api.start(categoryId, buyer);
    setScorecard(null);
    setNeg(n);
  }

  function reset() {
    setNeg(null);
    setScorecard(null);
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">⚖️</span>
          <div>
            <h1>Leverage</h1>
            <p>Multi-vendor negotiation, human in the loop</p>
          </div>
        </div>
        <div className="mode-pill" data-mode={mode}>
          {mode === "llm" ? "● Live AI" : mode === "mock" ? "● Demo (mock)" : "○ …"}
        </div>
      </header>

      {!neg ? (
        <Setup onStart={handleStart} />
      ) : (
        <Arena
          neg={neg}
          scorecard={scorecard}
          setNeg={setNeg}
          setScorecard={setScorecard}
          onReset={reset}
        />
      )}
    </div>
  );
}
