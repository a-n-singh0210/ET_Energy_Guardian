import { useEffect, useState } from "react";
import { api, fmt } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle, RiskBadge } from "../components/ui";

export default function Explanation() {
  const dates = useApi(api.explanationDates);
  const [selected, setSelected] = useState<string>("");

  useEffect(() => {
    if (dates.data && !selected) setSelected(dates.data.default);
  }, [dates.data, selected]);

  const exp = useApi(() => api.explanation(selected), [selected]);

  if (dates.loading) return <Loading />;
  if (dates.error || !dates.data) return <ErrorState message={dates.error ?? "no data"} />;

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <div className="text-sm text-ink/50 font-medium mb-1">Select a day</div>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="bg-cream rounded-xl px-4 py-2.5 font-semibold text-sm outline-none"
            >
              {dates.data.dates.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {exp.loading && <Loading />}
      {exp.error && <ErrorState message={exp.error} />}
      {exp.data && (
        <>
          <Card dark>
            <div className="flex items-center justify-between mb-3">
              <div className="text-gold text-sm font-semibold uppercase tracking-wide">Explanation · {exp.data.date}</div>
              <RiskBadge level={exp.data.trace.final.risk_level} large />
            </div>
            <p className="text-ivory/85 leading-relaxed whitespace-pre-line text-[15px]">{exp.data.text}</p>
          </Card>

          <Card>
            <SectionTitle title="Audit trail" subtitle="raw signals → anomalies → contributions → final score" />
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              <TraceStep title="Raw signals" rows={Object.entries(exp.data.trace.raw)
                .filter(([k]) => k !== "events_text" && k !== "n_events")
                .map(([k, v]) => [prettyKey(k), typeof v === "number" ? fmt(v, 2) : String(v || "—")])} />
              <TraceStep title="Anomaly scores" rows={Object.entries(exp.data.trace.anomalies).map(([k, v]) => [k, fmt(v)])} />
              <TraceStep title="Linear contrib." rows={Object.entries(exp.data.trace.linear_contributions).map(([k, v]) => [k, fmt(v)])} />
              <TraceStep title="Interactions" rows={Object.entries(exp.data.trace.interaction_contributions).map(([k, v]) => [k, fmt(v)])} />
              <TraceStep
                title="Final"
                highlight
                rows={[
                  ["linear", fmt(exp.data.trace.final.linear_total)],
                  ["interaction", fmt(exp.data.trace.final.interaction_total)],
                  ["score", fmt(exp.data.trace.final.compound_score)],
                ]}
              />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function TraceStep({
  title,
  rows,
  highlight = false,
}: {
  title: string;
  rows: [string, string][];
  highlight?: boolean;
}) {
  return (
    <div className={"rounded-2xl p-4 " + (highlight ? "bg-ink text-ivory" : "bg-cream/60")}>
      <div className={"text-xs font-semibold uppercase tracking-wide mb-2 " + (highlight ? "text-gold" : "text-ink/45")}>
        {title}
      </div>
      <div className="space-y-1.5">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between text-sm gap-2">
            <span className={highlight ? "text-ivory/60" : "text-ink/55"}>{k}</span>
            <span className="font-semibold tabular">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function prettyKey(k: string): string {
  return k.replace("brent_return", "brent ret").replace("freight_wci_ffill", "freight WCI").replace("event_severity_14", "sev 14d");
}
