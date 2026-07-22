import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { api, RISK_COLORS, type RiskLevel } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle, RiskBadge } from "../components/ui";

const CATEGORY_LABEL: Record<string, string> = {
  seizure: "Seizure",
  attack: "Attack",
  carrier_suspension: "Carrier suspension",
  military_action: "Military action",
};

export default function Timeline() {
  const { data, error, loading } = useApi(api.timeline);
  const ov = useApi(api.overview);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "no data"} />;

  const bounds = ov.data?.parameters.risk_levels.filter((r) => r.lower_bound) ?? [];

  return (
    <div className="space-y-5">
      <Card>
        <SectionTitle title="Compound risk over time" subtitle="Daily compound score across the analysis window" />
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data.score_series} margin={{ left: -10, right: 10, top: 10 }}>
            <defs>
              <linearGradient id="score" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#E8730C" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#E8730C" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#1a1a1888" }} minTickGap={40} />
            <YAxis tick={{ fontSize: 11, fill: "#1a1a1888" }} />
            <Tooltip contentStyle={tooltipStyle} />
            {bounds.map((b) => (
              <ReferenceLine
                key={b.level}
                y={b.lower_bound ?? 0}
                stroke={RISK_COLORS[b.level]}
                strokeDasharray="4 4"
                strokeOpacity={0.6}
              />
            ))}
            <Area type="monotone" dataKey="compound_score" stroke="#E8730C" strokeWidth={2} fill="url(#score)" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <SectionTitle title="Documented corridor events" subtitle="Curated from public reporting — see Assumptions for sources" />
        <div className="space-y-2">
          {data.events.map((e, i) => (
            <div key={i} className="flex items-center gap-4 bg-cream/50 rounded-2xl px-4 py-3">
              <div className="text-sm font-semibold tabular w-24 shrink-0 text-ink/70">{e.date}</div>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-ink text-ivory shrink-0">
                {CATEGORY_LABEL[e.category] ?? e.category}
              </span>
              <div className="text-sm flex-1">{e.event}</div>
              <div className="flex gap-1 shrink-0">
                {[1, 2, 3, 4, 5].map((s) => (
                  <span
                    key={s}
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: s <= e.severity ? "#E8730C" : "#00000015" }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

export const tooltipStyle = {
  borderRadius: 12,
  border: "none",
  boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
  fontSize: 12,
};

export function levelBadge(level: RiskLevel) {
  return <RiskBadge level={level} />;
}
