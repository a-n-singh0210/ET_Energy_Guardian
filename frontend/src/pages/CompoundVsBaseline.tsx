import {
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  ReferenceDot,
  Legend,
  LineChart,
} from "recharts";
import { api, fmt } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle } from "../components/ui";
import { tooltipStyle } from "./Timeline";

export default function CompoundVsBaseline() {
  const comp = useApi(api.compound);
  const cmp = useApi(api.compare);
  if (comp.loading || cmp.loading) return <Loading />;
  if (comp.error || cmp.error || !comp.data || !cmp.data)
    return <ErrorState message={comp.error ?? cmp.error ?? "no data"} />;

  const cAlerts = new Set(cmp.data.compound_alert_dates);
  const bAlerts = new Set(cmp.data.baseline_alert_dates);

  const series = comp.data.series.map((p) => ({ date: p.date, compound_score: p.compound_score }));
  const scoreByDate = new Map(series.map((p) => [p.date, p.compound_score]));
  const compoundMarks = [...cAlerts].map((d) => ({ date: d, y: scoreByDate.get(d) ?? 0 }));
  const baselineMarks = [...bAlerts].map((d) => ({ date: d, y: scoreByDate.get(d) ?? 0 }));

  const compound = cmp.data.comparison.find((c) => c.method === "compound");
  const baseline = cmp.data.comparison.find((c) => c.method === "baseline");

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <Card><Stat label="Compound alerts" value={compound?.alert_days} /></Card>
        <Card><Stat label="Compound TP / FP" value={`${compound?.tp} / ${compound?.fp}`} accent="#22A06B" /></Card>
        <Card><Stat label="Baseline alerts" value={baseline?.alert_days} /></Card>
        <Card><Stat label="Baseline TP / FP" value={`${baseline?.tp} / ${baseline?.fp}`} /></Card>
      </div>

      <Card>
        <SectionTitle
          title="Compound score with alerts vs documented disruptions"
          subtitle="○ compound alert · ▼ baseline alert · dashed grey = documented event · solid = systemic onset"
        />
        <ResponsiveContainer width="100%" height={360}>
          <LineChart data={series} margin={{ left: -10, right: 10, top: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#1a1a1888" }} minTickGap={40} />
            <YAxis domain={[-6, 6]} tick={{ fontSize: 11, fill: "#1a1a1888" }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            {cmp.data.gt_events.map((d) => (
              <ReferenceLine key={d} x={d} stroke="#00000022" strokeDasharray="3 3" />
            ))}
            <ReferenceLine x={cmp.data.systemic_onset} stroke="#1a1a18" strokeWidth={1.4}
              label={{ value: "onset", fontSize: 10, fill: "#1a1a18", position: "top" }} />
            <ReferenceLine y={cmp.data.compound_alert_threshold} stroke="#E8730C" strokeDasharray="5 5"
              label={{ value: "alert", fontSize: 10, fill: "#E8730C", position: "insideTopRight" }} />
            <Line type="monotone" dataKey="compound_score" name="Compound score" stroke="#E8730C" strokeWidth={2} dot={false} isAnimationActive={false} />
            {baselineMarks.map((m) => (
              <ReferenceDot key={"b" + m.date} x={m.date} y={m.y} r={5} fill="#2563EB" stroke="#fff" strokeWidth={1.5} />
            ))}
            {compoundMarks.map((m) => (
              <ReferenceDot key={"c" + m.date} x={m.date} y={m.y} r={7} fill="none" stroke="#DC3545" strokeWidth={2.5} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle title="Comparison metrics" subtitle="Against documented disruption events" />
          <table className="w-full text-sm">
            <thead>
              <tr className="text-ink/45 text-left">
                <th className="py-2 font-medium">Method</th>
                <th className="font-medium">Alerts</th>
                <th className="font-medium">Lead</th>
                <th className="font-medium">TP</th>
                <th className="font-medium">FN</th>
                <th className="font-medium">FP</th>
              </tr>
            </thead>
            <tbody>
              {cmp.data.comparison.map((r) => (
                <tr key={r.method} className={r.method === "compound" ? "bg-cream/60" : ""}>
                  <td className="py-2.5 font-semibold capitalize rounded-l-xl pl-2">{r.method}</td>
                  <td>{r.alert_days}</td>
                  <td>{r.lead_time_days === null ? "—" : `${r.lead_time_days}d`}</td>
                  <td className="text-risk-low font-semibold">{r.tp}</td>
                  <td>{r.fn}</td>
                  <td className="text-risk-severe font-semibold rounded-r-xl">{r.fp}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-ink/45 mt-3">
            Both first alert {fmt(compound?.lead_time_days ?? null, 0)} days before the systemic onset; the
            compound model adds detections on co-elevation days the baseline misses.
          </p>
        </Card>

        <Card>
          <SectionTitle title="Threshold sensitivity" subtitle="Compound alert threshold sweep" />
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={cmp.data.sensitivity} margin={{ left: -10, right: 10, top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
              <XAxis dataKey="threshold" tick={{ fontSize: 11, fill: "#1a1a1888" }} />
              <YAxis tick={{ fontSize: 11, fill: "#1a1a1888" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Line type="monotone" dataKey="tp" name="True pos." stroke="#22A06B" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="fp" name="False pos." stroke="#DC3545" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="fn" name="False neg." stroke="#E8730C" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="alert_days" name="Alerts" stroke="#2563EB" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div>
      <div className="text-sm text-ink/50 font-medium">{label}</div>
      <div className="text-3xl font-extrabold tabular mt-1" style={accent ? { color: accent } : {}}>
        {value}
      </div>
    </div>
  );
}
