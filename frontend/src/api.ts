import type {
  BuyerConfig,
  CategoryView,
  Negotiation,
  RoundResponse,
  Scorecard,
} from "./types";

async function http<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "content-type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<{ ok: boolean; mode: string; model: string }>("/api/health"),

  categories: () =>
    http<{ categories: CategoryView[] }>("/api/categories").then((r) => r.categories),

  start: (category_id: string, buyer: BuyerConfig) =>
    http<Negotiation>("/api/negotiations", {
      method: "POST",
      body: JSON.stringify({ category_id, buyer }),
    }),

  round: (
    id: string,
    body: { strategy?: string; target_vendor_id?: string; close_vendor_id?: string }
  ) =>
    http<RoundResponse>(`/api/negotiations/${id}/round`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  finish: (id: string, close_vendor_id?: string) =>
    http<{ negotiation: Negotiation; scorecard: Scorecard }>(
      `/api/negotiations/${id}/finish`,
      { method: "POST", body: JSON.stringify({ close_vendor_id }) }
    ),
};
