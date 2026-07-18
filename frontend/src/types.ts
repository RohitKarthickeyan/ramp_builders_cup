export interface Offer {
  price_per_seat: number;
  contract_length_months: number;
  free_seats: number;
  support_tier: "standard" | "priority" | "premium";
  notes?: string | null;
}

export interface Belief {
  est_floor: number;
  confidence: number;
  momentum: number;
  stalled_turns: number;
}

export interface Agent {
  id: string;
  kind: "buyer" | "vendor";
  name: string;
  color: string;
  status: string;
  activity: string;
  tagline?: string;
  persona?: string;
  list_price_per_seat?: number;
  current_offer?: Offer | null;
  price_history?: number[];
  walked_away?: boolean;
  deal_closed?: boolean;
  awaiting_reply?: boolean;
  turns?: number;
  belief?: Belief;
}

export interface Email {
  id: string;
  thread_id: string;
  sender_id: string;
  sender_role: "buyer" | "vendor";
  sender_name: string;
  to_id: string;
  to_name: string;
  subject: string;
  body: string;
  ts: number;
  offer?: Offer | null;
  is_followup: boolean;
}

export interface Thread {
  id: string;
  vendor_id: string;
  subject: string;
  emails: Email[];
}

export interface LogEntry {
  id: string;
  agent_id: string;
  agent_name: string;
  kind: "system" | "reasoning" | "strategy" | "research" | "email" | "action" | "coaching";
  text: string;
  ts: number;
}

export interface ResearchFinding {
  source: string;
  text: string;
  url?: string | null;
  price_per_seat?: number | null;
}

export interface ResearchReport {
  id: string;
  vendor_id: string;
  query: string;
  findings: ResearchFinding[];
  ts: number;
}

export interface Strategy {
  tactic: string;
  rationale: string;
  target_vendor_id: string | null;
  target_price: number | null;
  source: "default" | "coaching" | "auto";
}

export interface Contract {
  id: string;
  vendor_id: string;
  vendor_name: string;
  buyer_company: string;
  seats: number;
  price_per_seat: number;
  contract_length_months: number;
  free_seats: number;
  support_tier: string;
  annual_total: number;
  list_annual_total: number;
  savings: number;
  savings_pct: number;
  effective_date: string;
  clauses: string[];
  status: "draft" | "approved" | "rejected";
  ts: number;
}

export interface BuyerConfig {
  company: string;
  seats: number;
  budget_per_seat: number;
  priorities: string[];
  must_haves?: string[];
}

export interface NegState {
  id: string;
  mode: string;
  phase: "idle" | "negotiating" | "awaiting_approval" | "done";
  running: boolean;
  paused: boolean;
  buyer: BuyerConfig;
  strategy: Strategy;
  agents: Agent[];
  threads: Thread[];
  logs: LogEntry[];
  research: ResearchReport[];
  contract: Contract | null;
  winner_id: string | null;
  summary: string | null;
}
