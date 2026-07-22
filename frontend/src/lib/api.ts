// API client for the EnergyGuardian Flask backend. Display-only: the frontend
// never computes risk; it renders exactly what the API returns.

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:5001";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "SEVERE";

export interface ComparisonRow {
  method: string;
  alert_days: number;
  lead_time_days: number | null;
  tp: number;
  fn: number;
  fp: number;
}

export interface Overview {
  window: { start: string; end: string };
  n_days: number;
  peak: { date: string; score: number; risk_level: RiskLevel };
  risk_distribution: Partial<Record<RiskLevel, number>>;
  comparison: ComparisonRow[];
  signals: { key: string; label: string; role: string }[];
  parameters: {
    weights: Record<string, number>;
    lambda: number;
    risk_levels: { level: RiskLevel; lower_bound: number | null }[];
    baseline_thresholds: Record<string, number>;
    compound_alert_threshold: number;
  };
}

export interface EventRow {
  date: string;
  event: string;
  category: string;
  severity: number;
}
export interface ScorePoint {
  date: string;
  compound_score: number;
  risk_level: RiskLevel;
}
export interface Timeline {
  events: EventRow[];
  score_series: ScorePoint[];
}

export interface Signals {
  anomalies: Record<string, number | null>[];
  features: Record<string, number | null>[];
}

export interface CompoundPoint {
  date: string;
  signal_brent: number;
  signal_freight: number;
  signal_events: number;
  int_brent__freight: number;
  int_brent__events: number;
  int_freight__events: number;
  linear_total: number;
  interaction_total: number;
  compound_score: number;
  risk_level: RiskLevel;
}

export interface Compare {
  comparison: ComparisonRow[];
  compound_alert_dates: string[];
  baseline_alert_dates: string[];
  gt_events: string[];
  systemic_onset: string;
  compound_alert_threshold: number;
  sensitivity: {
    threshold: number;
    alert_days: number;
    tp: number;
    fn: number;
    fp: number;
    lead_time_days: number | null;
  }[];
}

export interface Explanation {
  date: string;
  text: string;
  trace: {
    raw: Record<string, number | string | null>;
    anomalies: Record<string, number>;
    linear_contributions: Record<string, number>;
    interaction_contributions: Record<string, number>;
    final: {
      linear_total: number;
      interaction_total: number;
      compound_score: number;
      risk_level: RiskLevel;
    };
  };
}

// --- India energy-security resilience types ---
export interface ParamMeta { value: number; unit: string; origin: string; source: string }
export interface IndiaContext {
  params: Record<string, ParamMeta>;
  import_mix: Record<string, number>;
  import_mix_source: string;
  presets: Record<string, { hormuz_closure: number; redsea_suspension: number; opec_cut_mbd: number }>;
  geo: GeoPayload;
}
export interface GeoNode { name: string; lat: number; lng: number; corridor?: string }
export interface GeoRoute { supplier: string; name: string; corridor: string; points: [number, number][] }
export interface GeoPayload {
  chokepoints: Record<string, GeoNode>;
  india_ports: Record<string, GeoNode>;
  suppliers: Record<string, GeoNode>;
  routes: GeoRoute[];
}
export interface ScenarioResult {
  input: { hormuz_closure: number; redsea_suspension: number; opec_cut_mbd: number };
  india_import_gap_mbd: number;
  hormuz_gap_mbd: number;
  redsea_gap_mbd: number;
  global_supply_loss_mbd: number;
  global_loss_fraction: number;
  brent_baseline_usd: number;
  brent_premium_pct: number;
  brent_price_usd: number;
  spr_bridge_days: number | null;
  retail_fuel_delta_pct: number;
  gdp_growth_hit_pp: number;
  cad_widen_pct_gdp: number;
  inflation_add_bps: number;
  refinery_runrate_pct: number;
  refinery_runrate_at_risk_pct: number;
  gdp_trajectory: { month: number; managed_pp: number; reactive_pp: number }[];
  severity: RiskLevel;
  reasoning: string[];
}
export interface ProcRec {
  name: string; origin: string; corridor: string; grade: string; api: number;
  sulfur_pct: number; transit_days: number; premium_usd: number; landed_usd: number;
  spare_mbd: number; allocated_mbd: number; compat: number; status: string;
}
export interface Procurement {
  gap_mbd: number; coverage_mbd: number; coverage_pct: number; residual_gap_mbd: number;
  blended_landed_usd: number | null; first_cargo_eta_days: number | null; recommendations: ProcRec[];
}
export interface SprPoint { day: number; spr_remaining_mmbbl: number; alt_supply_mbd: number; spr_draw_mbd: number; uncovered_mbd: number }
export interface Spr {
  bridged: boolean; verdict: string; exposure_days: number; exhausted_day: number | null;
  first_cargo_eta_days: number; full_resupply_day: number; spr_min_mmbbl: number; schedule: SprPoint[];
}
export interface SimMatch { name: string; year: number; similarity: number; price_shock_pct: number; supply_loss_mbd: number; note: string }
export interface PipelineStep {
  step: number; name: string; role: string; inputs: string[]; reasoning: string;
  output: string; decision: string; compute_ms: number; status: string;
}
export interface Resilience {
  scenario: ScenarioResult; procurement: Procurement; spr: Spr; similarity: SimMatch[]; disrupted_corridors: string[];
  pipeline: PipelineStep[]; total_compute_ms: number;
}

export interface GraphNode {
  id: string; label: string; kind: "supplier" | "corridor" | "grade" | "refinery";
  key?: string; disrupted?: boolean; risk?: number | null; grade?: string; spare_mbd?: number;
}
export interface GraphEdge { source: string; target: string; kind: string }
export interface GraphImpact {
  cut_off_suppliers: string[]; resilient_suppliers: string[]; at_risk_volume_mbd: number; at_risk_grades: string[];
}
export interface Graph {
  nodes: GraphNode[]; edges: GraphEdge[]; stats: Record<string, number>; impact?: GraphImpact;
}

export interface IntelEvent {
  title: string; source: string; corridor: string; supplier: string;
  event_type: string; severity: number; confidence: number; method: string;
}
export interface Intel {
  generated_at: string;
  method: string;
  headline_count: number;
  corridor_scores: Record<string, number>;
  supplier_scores: Record<string, number>;
  top_events: IntelEvent[];
  cache_age_seconds: number;
}

export interface ExtractResult {
  ok: boolean;
  error?: string;
  method: string;
  corridor: string;
  supplier: string;
  event_type: string;
  severity: number;
  confidence: number;
  rationale: string;
  intensity: number;
  suggested_knobs: { h: number; r: number; o: number };
}

export interface Chokepoint {
  name: string; corridor: string; lat: number; lon: number;
  vessel_total: number; vessel_tanker: number; tanker_share: number;
}
export interface Ais { chokepoints: Chokepoint[]; source: string }
export interface RagSource { id: string; text: string; source: string; score: number | null }
export interface Ask {
  query: string; answer: string | null; generated: boolean; retrieval: string; sources: RagSource[];
}

export const api = {
  overview: () => get<Overview>("/api/overview"),
  indiaContext: () => get<IndiaContext>("/api/india/context"),
  intel: (refresh = false) => get<Intel>(`/api/intel${refresh ? "?refresh=1" : ""}`),
  extractArticle: (text: string) => post<ExtractResult>("/api/extract", { text }),
  ais: () => get<Ais>("/api/ais"),
  askSamples: () => get<{ samples: string[] }>("/api/ask"),
  ask: (q: string) => get<Ask>(`/api/ask?q=${encodeURIComponent(q)}`),
  resilience: (hormuz: number, redsea: number, opec: number) =>
    get<Resilience>(`/api/resilience?hormuz=${hormuz}&redsea=${redsea}&opec=${opec}`),
  graph: (hormuz: number, redsea: number) =>
    get<Graph>(`/api/graph?hormuz=${hormuz}&redsea=${redsea}`),
  timeline: () => get<Timeline>("/api/timeline"),
  signals: () => get<Signals>("/api/signals"),
  compound: () => get<{ series: CompoundPoint[] }>("/api/compound"),
  compare: () => get<Compare>("/api/compare"),
  explanationDates: () => get<{ dates: string[]; default: string }>("/api/explanation/dates"),
  explanation: (date: string) =>
    get<Explanation>(`/api/explanation?date=${date}`),
  assumptions: () => get<{ markdown: string }>("/api/assumptions"),
};

export const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: "#22A06B",
  MODERATE: "#E0A92E",
  HIGH: "#E8730C",
  SEVERE: "#DC3545",
};

export function fmt(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}
