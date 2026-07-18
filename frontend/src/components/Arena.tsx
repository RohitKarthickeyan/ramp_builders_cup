import { useMemo, useState } from "react";
import { api } from "../api";
import type { Negotiation, Scorecard as ScorecardType } from "../types";
import StrategyBar, { StrategyCard } from "./StrategyBar";
import VendorThread from "./VendorThread";
import PriceChart from "./PriceChart";
import Scorecard from "./Scorecard";

export default function Arena({
  neg,
  scorecard,
  setNeg,
  setScorecard,
  onReset,
}: {
  neg: Negotiation;
  scorecard: ScorecardType | null;
  setNeg: (n: Negotiation) => void;
  setScorecard: (s: ScorecardType | null) => void;
  onReset: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPlay, setLastPlay] = useState<string>("");

  const bestId = useMemo(() => {
    let best: string | null = null;
    let bestPrice = Infinity;
    for (const v of neg.vendors) {
      if (v.walked_away || !v.current_offer) continue;
      if (v.current_offer.price_per_seat < bestPrice) {
        bestPrice = v.current_offer.price_per_seat;
        best = v.id;
      }
    }
    return best;
  }, [neg]);

  async function runRound(strategy: string, targetVendorId?: string, label?: string) {
    setBusy(true);
    setError(null);
    setLastPlay(label ?? (strategy ? strategy : "Ran a round"));
    try {
      const res = await api.round(neg.id, {
        strategy: strategy || undefined,
        target_vendor_id: targetVendorId,
      });
      setNeg(res.negotiation);
      if (res.scorecard) setScorecard(res.scorecard);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function onPlayCard(card: StrategyCard, targetVendorId?: string) {
    const label =
      card.emoji + " " + card.label + (targetVendorId ? ` → ${targetVendorId}` : "");
    runRound(card.prompt, targetVendorId, label);
  }

  async function closeWith(vendorId: string) {
    setBusy(true);
    try {
      const res = await api.round(neg.id, { close_vendor_id: vendorId });
      setNeg(res.negotiation);
      if (res.scorecard) setScorecard(res.scorecard);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="arena">
      <div className="arena-main">
        <div className="threads">
          {neg.vendors.map((v) => (
            <VendorThread
              key={v.id}
              v={v}
              isBest={v.id === bestId}
              budget={neg.buyer.budget_per_seat}
              onClose={closeWith}
              finished={neg.finished}
            />
          ))}
        </div>
      </div>

      <aside className="arena-side">
        <PriceChart neg={neg} />
        {lastPlay && (
          <div className="last-play">
            <span className="muted small">Last move</span>
            <div>{lastPlay}</div>
          </div>
        )}
        {error && <div className="error">{error}</div>}
        {!neg.finished ? (
          <StrategyBar
            vendors={neg.vendors}
            busy={busy}
            round={neg.round}
            maxRounds={neg.max_rounds}
            onPlay={onPlayCard}
            onFreeText={(t) => runRound(t, undefined, t ? `💬 “${t}”` : "▶ Ran a round")}
          />
        ) : (
          <div className="finished-note">
            <p>Negotiation finished.</p>
            <button className="ghost" onClick={onReset}>
              Start over
            </button>
          </div>
        )}
      </aside>

      {scorecard && neg.finished && <Scorecard sc={scorecard} onReset={onReset} />}
    </div>
  );
}
