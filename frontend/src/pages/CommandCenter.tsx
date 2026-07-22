import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Legend, Line,
} from "recharts";
import { api, fmt, type RiskLevel, type PipelineStep } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle, RiskBadge } from "../components/ui";
import { tooltipStyle } from "./Timeline";

const PRESETS: { label: string; h: number; r: number; o: number }[] = [
  { label: "Calm baseline", h: 0, r: 0, o: 0 },
  { label: "Red Sea suspension", h: 0, r: 0.8, o: 0 },
  { label: "Hormuz partial 30%", h: 0.3, r: 0.2, o: 0 },
  { label: "Hormuz major + OPEC+", h: 0.6, r: 0.3, o: 1 },
  { label: "Hormuz full closure", h: 1, r: 0.5, o: 0 },
];

export default function CommandCenter({ knobs, setKnobs }: {
  knobs?: { h: number; r: number; o: number };
  setKnobs?: (k: { h: number; r: number; o: number }) => void;
}) {
  const [local, setLocal] = useState({ h: 0.6, r: 0.3, o: 1 });
  const k = knobs ?? local;
  const update = setKnobs ?? setLocal;
  const { h, r, o } = k;
  const setH = (v: number) => update({ ...k, h: v });
  const setR = (v: number) => update({ ...k, r: v });
  const setO = (v: number) => update({ ...k, o: v });
  const { data, error, loading } = useApi(() => api.resilience(h, r, o), [h, r, o]);

  return (
    <div className="space-y-5">
      {/* Controls */}
      <Card>
        <SectionTitle title="Disruption scenario" subtitle="Drag the knobs or pick a preset — the full impact cascade updates live" />
        <div className="flex flex-wrap gap-2 mb-5">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => update({ h: p.h, r: p.r, o: p.o })}
              className="px-3.5 py-1.5 rounded-full text-sm font-semibold bg-cream hover:bg-sand transition"
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Slider label="Strait of Hormuz closure" value={h} onChange={setH} max={1} step={0.05} fmt={(v) => `${Math.round(v * 100)}%`} />
          <Slider label="Red Sea suspension" value={r} onChange={setR} max={1} step={0.05} fmt={(v) => `${Math.round(v * 100)}%`} />
          <Slider label="OPEC+ emergency cut" value={o} onChange={setO} max={3} step={0.1} fmt={(v) => `${v.toFixed(1)} mb/d`} />
        </div>
      </Card>

      {loading && <Loading />}
      {error && <ErrorState message={error} />}
      {data && (
        <>
          {/* Impact cascade KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Metric label="Brent" value={`$${fmt(data.scenario.brent_price_usd, 0)}`} sub={`+${fmt(data.scenario.brent_premium_pct, 0)}%`} accent="#E8730C" />
            <Metric label="Import gap" value={`${fmt(data.scenario.india_import_gap_mbd)}`} sub="mb/d at risk" />
            <Metric label="SPR bridge" value={data.scenario.spr_bridge_days ? `${fmt(data.scenario.spr_bridge_days, 0)}d` : "—"} sub="reserve cover" />
            <Metric label="GDP growth" value={`−${fmt(data.scenario.gdp_growth_hit_pp)}`} sub="pp" accent="#DC3545" />
            <Metric label="CAD" value={`+${fmt(data.scenario.cad_widen_pct_gdp)}%`} sub="of GDP" />
            <Metric label="Fuel price" value={`+${fmt(data.scenario.retail_fuel_delta_pct, 0)}%`} sub="retail" />
          </div>

          {/* Severity + reasoning */}
          <Card dark>
            <div className="flex items-center justify-between mb-3">
              <div className="text-gold text-sm font-semibold uppercase tracking-wide">Scenario impact · signal → cascade</div>
              <RiskBadge level={data.scenario.severity as RiskLevel} large />
            </div>
            <ol className="space-y-1.5">
              {data.scenario.reasoning.map((step, i) => (
                <li key={i} className="text-sm text-ivory/80 flex gap-3">
                  <span className="text-gold font-bold tabular">{i + 1}</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </Card>

          {/* AI decision pipeline — inspectable execution trace */}
          <Card>
            <SectionTitle
              title="AI decision pipeline"
              subtitle="Five engines run in sequence over a shared context. Expand any step to inspect its input, reasoning and output. (The LLM news-extraction step runs upstream — see Risk Intel.)"
            />
            <PipelineTrace steps={data.pipeline} />
          </Card>

          {/* Refinery run-rate + GDP trajectory */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <Card>
              <SectionTitle title="Refinery run-rate at risk" subtitle="Unmitigated, before SPR / rerouting" />
              <div className="flex items-end gap-3 mt-2">
                <div className="text-5xl font-extrabold tabular" style={{ color: data.scenario.refinery_runrate_pct < 80 ? "#E8730C" : "#22A06B" }}>
                  {fmt(data.scenario.refinery_runrate_pct, 0)}%
                </div>
                <div className="text-ink/50 text-sm mb-2">run-rate</div>
              </div>
              <div className="h-3 rounded-full bg-cream overflow-hidden mt-3">
                <div className="h-full bg-risk-low inline-block" style={{ width: `${data.scenario.refinery_runrate_pct}%` }} />
                <div className="h-full bg-risk-severe inline-block" style={{ width: `${data.scenario.refinery_runrate_at_risk_pct}%` }} />
              </div>
              <div className="text-xs text-ink/45 mt-2">
                {fmt(data.scenario.refinery_runrate_at_risk_pct, 0)}% of throughput at risk until supply is backfilled.
              </div>
            </Card>
            <Card className="lg:col-span-2">
              <SectionTitle title="GDP-growth impact trajectory" subtitle="Managed response vs reactive (McKinsey: +47 days to stabilise without response intelligence)" />
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={data.scenario.gdp_trajectory} margin={{ left: -8, right: 10, top: 6 }}>
                  <defs>
                    <linearGradient id="mg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#22A06B" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#22A06B" stopOpacity={0.03} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
                  <XAxis dataKey="month" tickFormatter={(m) => `M${m}`} tick={{ fontSize: 11, fill: "#1a1a1888" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#1a1a1888" }} label={{ value: "pp", fontSize: 10, position: "insideLeft" }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Area type="monotone" dataKey="reactive_pp" name="Reactive (no system)" stroke="#DC3545" fill="none" strokeWidth={2} strokeDasharray="5 4" isAnimationActive={false} />
                  <Area type="monotone" dataKey="managed_pp" name="Managed (EnergyGuardian)" stroke="#22A06B" fill="url(#mg)" strokeWidth={2} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Procurement orchestrator */}
          <Card>
            <SectionTitle
              title="Adaptive procurement — executable rerouting"
              subtitle={
                data.disrupted_corridors.length
                  ? `Corridors disrupted: ${data.disrupted_corridors.join(", ")} — orchestrator avoids them`
                  : "No corridor disrupted — baseline sourcing"
              }
            />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <Metric label="Coverage" value={`${fmt(data.procurement.coverage_pct, 0)}%`} sub={`${fmt(data.procurement.coverage_mbd)} mb/d`} accent="#22A06B" />
              <Metric label="Blended landed" value={data.procurement.blended_landed_usd ? `$${fmt(data.procurement.blended_landed_usd, 0)}` : "—"} sub="USD/bbl" />
              <Metric label="First cargo" value={data.procurement.first_cargo_eta_days ? `${data.procurement.first_cargo_eta_days}d` : "—"} sub="ETA to India" />
              <Metric label="Residual gap" value={`${fmt(data.procurement.residual_gap_mbd)}`} sub="mb/d uncovered" accent={data.procurement.residual_gap_mbd > 0 ? "#DC3545" : undefined} />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-ink/45 text-left">
                    {["Source", "Origin", "Grade", "Corridor", "Transit", "Landed $", "Allocated", ""].map((c) => (
                      <th key={c} className="py-2 font-medium">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.procurement.recommendations.map((rec) => (
                    <tr key={rec.name} className={rec.status === "selected" ? "bg-risk-low/10" : rec.status === "disrupted" ? "opacity-40" : ""}>
                      <td className="py-2 font-semibold rounded-l-lg pl-2">{rec.name}</td>
                      <td>{rec.origin}</td>
                      <td className="text-ink/60">{rec.grade}</td>
                      <td className="text-ink/60">{rec.corridor.replace("atlantic_cape", "Atlantic/Cape").replace("hormuz", "Hormuz").replace("redsea", "Red Sea")}</td>
                      <td>{rec.transit_days}d</td>
                      <td className="tabular">${fmt(rec.landed_usd, 0)}</td>
                      <td className="tabular font-semibold">{rec.allocated_mbd > 0 ? `${fmt(rec.allocated_mbd)}` : "—"}</td>
                      <td className="rounded-r-lg pr-2">{statusChip(rec.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* SPR + similarity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card>
              <SectionTitle title="SPR drawdown bridge" subtitle="Can the reserve cover the gap until rerouted cargoes ramp in?" />
              <div className={"text-sm mb-3 px-3 py-2 rounded-xl " + (data.spr.bridged ? "bg-risk-low/15 text-risk-low" : "bg-risk-severe/15 text-risk-severe")}>
                {data.spr.verdict}
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={data.spr.schedule} margin={{ left: -8, right: 10, top: 6 }}>
                  <defs>
                    <linearGradient id="spr" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563EB" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#2563EB" stopOpacity={0.03} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#1a1a1888" }} label={{ value: "day", fontSize: 10, position: "insideBottomRight", offset: -2 }} />
                  <YAxis tick={{ fontSize: 11, fill: "#1a1a1888" }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  {data.spr.first_cargo_eta_days != null && (
                    <ReferenceLine x={data.spr.first_cargo_eta_days} stroke="#22A06B" strokeDasharray="4 4" label={{ value: "1st cargo", fontSize: 9, fill: "#22A06B", position: "top" }} />
                  )}
                  <Area type="monotone" dataKey="spr_remaining_mmbbl" name="SPR (mmbbl)" stroke="#2563EB" fill="url(#spr)" isAnimationActive={false} />
                  <Line type="monotone" dataKey="alt_supply_mbd" name="Alt supply (mb/d)" stroke="#22A06B" strokeWidth={2} dot={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            <Card>
              <SectionTitle title="Historical analogues" subtitle="Most similar past shocks (structured-feature similarity)" />
              <div className="space-y-3">
                {data.similarity.map((m) => (
                  <div key={m.name} className="bg-cream/50 rounded-2xl px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold">{m.name} <span className="text-ink/40 font-normal">· {m.year}</span></div>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 rounded-full bg-sand overflow-hidden">
                          <div className="h-full bg-gold" style={{ width: `${m.similarity * 100}%` }} />
                        </div>
                        <span className="text-sm font-bold tabular">{m.similarity.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="text-xs text-ink/55 mt-1">{m.note}</div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function PipelineTrace({ steps }: { steps: PipelineStep[] }) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (n: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(n) ? next.delete(n) : next.add(n);
      return next;
    });

  return (
    <div className="relative">
      {/* vertical spine */}
      <div className="absolute left-[15px] top-3 bottom-3 w-px bg-ink/10" aria-hidden />
      <div className="space-y-2">
        {steps.map((s) => {
          const isOpen = open.has(s.step);
          const failed = s.status === "error";
          return (
            <div key={s.step} className="relative">
              <button
                onClick={() => toggle(s.step)}
                className="w-full flex items-start gap-3 text-left group"
              >
                {/* numbered node */}
                <span
                  className={
                    "relative z-10 shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold tabular " +
                    (failed ? "bg-risk-severe text-white" : "bg-ink text-gold")
                  }
                >
                  {s.step}
                </span>
                <span className="flex-1 min-w-0 bg-cream/50 group-hover:bg-cream rounded-2xl px-4 py-2.5 transition">
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-bold text-sm">{s.name}</span>
                    <span className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] font-mono text-ink/30">{fmt(s.compute_ms, 2)}ms local</span>
                      <span className={"text-ink/40 transition-transform " + (isOpen ? "rotate-90" : "")}>›</span>
                    </span>
                  </span>
                  <span className="block text-xs text-ink/70 mt-0.5 leading-snug">{s.decision}</span>
                </span>
              </button>

              {isOpen && (
                <div className="ml-11 mt-1.5 mb-1 rounded-2xl border border-ink/10 bg-white/60 overflow-hidden text-sm">
                  <TraceRow label="Input">
                    <div className="flex flex-wrap gap-1.5">
                      {s.inputs.map((x, j) => (
                        <span key={j} className="text-xs font-medium bg-cream rounded-full px-2.5 py-0.5 text-ink/70">
                          {x}
                        </span>
                      ))}
                    </div>
                  </TraceRow>
                  <TraceRow label="Reasoning">
                    <span className="text-ink/70 leading-snug">{s.reasoning}</span>
                  </TraceRow>
                  <TraceRow label="Output" last>
                    <span className="font-semibold text-ink leading-snug">{s.output}</span>
                  </TraceRow>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TraceRow({ label, children, last }: { label: string; children: React.ReactNode; last?: boolean }) {
  return (
    <div className={"flex gap-3 px-4 py-2.5 " + (last ? "" : "border-b border-ink/[0.06]")}>
      <div className="w-[72px] shrink-0 text-[10px] font-bold uppercase tracking-[0.12em] text-goldDeep pt-0.5">
        {label}
      </div>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}

function Slider({ label, value, onChange, max, step, fmt: f }: {
  label: string; value: number; onChange: (v: number) => void; max: number; step: number; fmt: (v: number) => string;
}) {
  return (
    <div>
      <div className="flex justify-between mb-2">
        <span className="text-sm font-medium text-ink/60">{label}</span>
        <span className="text-sm font-bold tabular">{f(value)}</span>
      </div>
      <input
        type="range" min={0} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-gold"
      />
    </div>
  );
}

function Metric({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: string }) {
  return (
    <Card className="!p-4">
      <div className="text-xs text-ink/50 font-medium">{label}</div>
      <div className="text-2xl font-extrabold tabular mt-0.5" style={accent ? { color: accent } : {}}>{value}</div>
      {sub && <div className="text-xs text-ink/40 mt-0.5">{sub}</div>}
    </Card>
  );
}

function statusChip(status: string) {
  const map: Record<string, [string, string]> = {
    selected: ["Selected", "#22A06B"],
    standby: ["Standby", "#8A8A80"],
    disrupted: ["Disrupted", "#DC3545"],
  };
  const [label, color] = map[status] ?? [status, "#8A8A80"];
  return <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ backgroundColor: color + "22", color }}>{label}</span>;
}
