import { useCallback, useEffect, useRef, useState } from "react";
import type { NegState } from "./types";

export type OutMsg =
  | { type: "start" }
  | { type: "coach"; text: string }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "stop" }
  | { type: "approve_contract" }
  | { type: "reject_contract"; note: string };

export function useNegotiation(negId: string | null) {
  const [state, setState] = useState<NegState | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!negId) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/negotiations/${negId}/ws`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "state") setState(msg.state as NegState);
    };
    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [negId]);

  const send = useCallback((msg: OutMsg) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
  }, []);

  return { state, connected, send };
}
