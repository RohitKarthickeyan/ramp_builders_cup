import type { BuyerConfig, NegState } from "./types";

async function http<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "content-type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<{ ok: boolean; mode: string; model: string }>("/api/health"),
  create: (buyer: BuyerConfig) =>
    http<{ id: string; state: NegState }>("/api/negotiations", {
      method: "POST",
      body: JSON.stringify({ category_id: "coding", buyer }),
    }),
};
