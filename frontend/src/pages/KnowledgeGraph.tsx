import { useMemo, useState } from "react";
import { api, type GraphNode } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle } from "../components/ui";

const PRESETS = [
  { label: "No disruption", h: 0, r: 0 },
  { label: "Red Sea disrupted", h: 0, r: 0.8 },
  { label: "Hormuz disrupted", h: 0.6, r: 0 },
  { label: "Hormuz + Red Sea", h: 0.6, r: 0.5 },
];

const VW = 1000, VH = 620, PAD = 60;
const COLS: Record<string, number> = { supplier: PAD, corridor: VW / 2, refinery: VW - PAD };

function riskColor(p?: number | null): string {
  if (p == null) return "#8A8A80";
  if (p >= 0.75) return "#DC3545";
  if (p >= 0.5) return "#E8730C";
  if (p >= 0.25) return "#E0A92E";
  return "#22A06B";
}

export default function KnowledgeGraph() {
  const [preset, setPreset] = useState(3);
  const p = PRESETS[preset];
  const { data, error, loading } = useApi(() => api.graph(p.h, p.r), [preset]);
  const [hover, setHover] = useState<string | null>(null);

  const layout = useMemo(() => {
    if (!data) return null;
    // Only supplier / corridor / refinery are placed on the canvas (grades are
    // shown as a property of suppliers to keep the graph readable).
    const byKind: Record<string, GraphNode[]> = { supplier: [], corridor: [], refinery: [] };
    data.nodes.forEach((n) => { if (byKind[n.kind]) byKind[n.kind].push(n); });
    const pos: Record<string, { x: number; y: number; n: GraphNode }> = {};
    (["supplier", "corridor", "refinery"] as const).forEach((kind) => {
      const list = byKind[kind];
      list.forEach((n, i) => {
        const y = PAD + (i + 0.5) * ((VH - 2 * PAD) / list.length);
        pos[n.id] = { x: COLS[kind], y, n };
      });
    });
    const edges = data.edges.filter((e) => pos[e.source] && pos[e.target] &&
      (e.kind === "ships_via" || e.kind === "delivers_to"));
    return { pos, edges };
  }, [data]);

  if (loading) return <Loading />;
  if (error || !data || !layout) return <ErrorState message={error ?? "no graph"} />;

  const impact = data.impact;
  const cutOff = new Set(impact?.cut_off_suppliers ?? []);

  const connected = (id: string): Set<string> => {
    const set = new Set<string>([id]);
    layout.edges.forEach((e) => {
      if (e.source === id) set.add(e.target);
      if (e.target === id) set.add(e.source);
    });
    return set;
  };
  const hi = hover ? connected(hover) : null;

  return (
    <div className="space-y-5">
      <Card>
        <SectionTitle
          title="Supply knowledge graph"
          subtitle={`${data.stats.suppliers} suppliers · ${data.stats.corridors} corridors · ${data.stats.grades} grades · ${data.stats.refineries} refineries · ${data.stats.edges} relationships`}
        />
        <div className="flex flex-wrap gap-2 mb-3">
          {PRESETS.map((pr, i) => (
            <button key={pr.label} onClick={() => setPreset(i)}
              className={"px-3.5 py-1.5 rounded-full text-sm font-semibold transition " +
                (i === preset ? "bg-ink text-ivory" : "bg-cream hover:bg-sand")}>
              {pr.label}
            </button>
          ))}
        </div>
        <div className="rounded-2xl bg-[#FBF8F0] overflow-hidden">
          <svg viewBox={`0 0 ${VW} ${VH}`} className="w-full h-auto">
            {/* column headers */}
            {[["Suppliers", COLS.supplier], ["Corridors", COLS.corridor], ["India refineries", COLS.refinery]].map(([t, x]) => (
              <text key={t as string} x={x as number} y={28} textAnchor="middle" fontSize={14} fontWeight={700} fill="#1a1a18">{t}</text>
            ))}
            {/* edges */}
            {layout.edges.map((e, i) => {
              const a = layout.pos[e.source], b = layout.pos[e.target];
              const active = hi ? hi.has(e.source) && hi.has(e.target) : true;
              const disruptedEdge = b.n.kind === "corridor" ? b.n.disrupted : a.n.kind === "corridor" ? a.n.disrupted : false;
              const cut = cutOff.has(a.n.label) || cutOff.has(b.n.label);
              const mx = (a.x + b.x) / 2;
              return (
                <path key={i} d={`M${a.x},${a.y} C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`}
                  fill="none" stroke={cut || disruptedEdge ? "#DC3545" : "#22A06B"}
                  strokeWidth={hover ? (active ? 2 : 0.4) : 1.1}
                  strokeOpacity={hover ? (active ? 0.9 : 0.12) : (cut || disruptedEdge ? 0.55 : 0.28)}
                  strokeDasharray={disruptedEdge ? "5 4" : undefined} />
              );
            })}
            {/* nodes */}
            {Object.values(layout.pos).map(({ x, y, n }) => {
              const dim = hover && hi && !hi.has(n.id);
              let fill = "#3A362D", label2 = "";
              if (n.kind === "corridor") { fill = n.disrupted ? "#DC3545" : riskColor(n.risk); label2 = n.risk != null ? `${Math.round(n.risk * 100)}%` : ""; }
              else if (n.kind === "refinery") fill = "#E0A92E";
              else fill = cutOff.has(n.label) ? "#DC3545" : "#4A6E5D";
              const r = n.kind === "corridor" ? 11 : 7;
              const anchor = n.kind === "supplier" ? "start" : n.kind === "refinery" ? "end" : "middle";
              const tx = n.kind === "supplier" ? x + 13 : n.kind === "refinery" ? x - 13 : x;
              const ty = n.kind === "corridor" ? y - 18 : y + 4;
              return (
                <g key={n.id} opacity={dim ? 0.25 : 1}
                   onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} style={{ cursor: "pointer" }}>
                  <circle cx={x} cy={y} r={r} fill={fill} stroke="#FBF8F0" strokeWidth={2} />
                  <text x={tx} y={ty} textAnchor={anchor} fontSize={11.5}
                    fontWeight={n.kind === "corridor" ? 700 : 600}
                    fill={cutOff.has(n.label) ? "#B02533" : "#1a1a18"}
                    stroke="#FBF8F0" strokeWidth={2.6} paintOrder="stroke" strokeLinejoin="round">
                    {n.label}{n.kind === "supplier" && n.grade ? ` · ${n.grade}` : ""}
                  </text>
                  {label2 && <text x={x} y={y + 4} textAnchor="middle" fontSize={9} fontWeight={700} fill="#fff">{label2}</text>}
                </g>
              );
            })}
          </svg>
        </div>
        <div className="text-xs text-ink/45 mt-2">Hover any node to trace its relationships. Corridor nodes show live disruption probability; red = disrupted or cut-off.</div>
      </Card>

      {impact && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          <Card><Stat label="Suppliers cut off" value={impact.cut_off_suppliers.length} accent="#DC3545" /></Card>
          <Card><Stat label="Import volume at risk" value={`${impact.at_risk_volume_mbd}`} sub="mb/d" accent="#E8730C" /></Card>
          <Card><Stat label="Resilient suppliers" value={impact.resilient_suppliers.length} accent="#22A06B" /></Card>
          <Card><Stat label="Grades at risk" value={impact.at_risk_grades.length || "—"} /></Card>
        </div>
      )}
      {impact && impact.cut_off_suppliers.length > 0 && (
        <Card dark>
          <div className="text-gold text-sm font-semibold uppercase tracking-wide mb-1">Graph-traversal impact</div>
          <p className="text-ivory/85 text-sm">
            Disrupting {p.label.toLowerCase()} cuts off <b>{impact.cut_off_suppliers.join(", ")}</b> — every corridor they
            ship through is compromised — putting <b>{impact.at_risk_volume_mbd} mb/d</b> at risk. Resilient Atlantic/Cape
            suppliers ({impact.resilient_suppliers.join(", ")}) remain reachable.
          </p>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: string }) {
  return (
    <div>
      <div className="text-sm text-ink/50 font-medium">{label}</div>
      <div className="text-3xl font-extrabold tabular mt-1" style={accent ? { color: accent } : {}}>{value}</div>
      {sub && <div className="text-xs text-ink/40 mt-0.5">{sub}</div>}
    </div>
  );
}
