export interface Offer {
  price_per_seat: number;
  contract_length_months: number;
  free_seats: number;
  support_tier: "standard" | "priority" | "premium";
}

export interface Message {
  speaker: "buyer" | "vendor";
  text: string;
  reasoning?: string | null;
  offer?: Offer | null;
  round: number;
  walk_away: boolean;
}

export interface VendorView {
  id: string;
  name: string;
  tagline: string;
  persona: string;
  color: string;
  list_price_per_seat: number;
  messages: Message[];
  current_offer: Offer | null;
  walked_away: boolean;
  deal_closed: boolean;
  price_history: (number | null)[];
  annual_total: number | null;
  list_annual_total: number;
}

export interface BuyerConfig {
  seats: number;
  budget_per_seat: number;
  priorities: string[];
  must_haves: string[];
}

export interface Negotiation {
  id: string;
  category: string;
  buyer: BuyerConfig;
  round: number;
  max_rounds: number;
  finished: boolean;
  winner_id: string | null;
  vendors: VendorView[];
}

export interface ScoreRow {
  vendor_id: string;
  name: string;
  score: number;
  final_price_per_seat: number | null;
  contract_length_months: number | null;
  free_seats: number;
  support_tier: string | null;
  annual_total: number | null;
  list_annual_total: number;
  savings: number;
  savings_pct: number;
  walked_away: boolean;
}

export interface Scorecard {
  winner: ScoreRow | null;
  rows: ScoreRow[];
}

export interface RoundResponse {
  negotiation: Negotiation;
  scorecard: Scorecard | null;
}

export interface CategoryView {
  id: string;
  label: string;
  description: string;
  vendors: Pick<
    VendorView,
    "id" | "name" | "tagline" | "persona" | "color" | "list_price_per_seat"
  >[];
}
