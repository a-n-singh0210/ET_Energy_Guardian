import { api, RISK_COLORS, fmt, type RiskLevel } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Kpi, Loading, ErrorState, RiskBadge, SectionTitle } from "../components/ui";

const RISK_ORDER: RiskLevel[] = ["LOW", "MODERATE", "HIGH", "SEVERE"];

export default function Overview() {
  const { data, error, loading } = useApi(api.overview);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "no data"} />;

  const compound = data.comparison.find((c) => c.method === "compound");
  const baseline = data.comparison.find((c) => c.method === "baseline");
  const dist = RISK_ORDER.filter((r) => data.risk_distribution[r]).map((r) => ({
    name: r,
    value: data.risk_distribution[r] ?? 0,
  }));

  return (
    <div className="space-y-5">
      {/* KPI strip */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <Card>
          <Kpi label="Days analysed" value={data.n_days} sub={`${data.window.start} → ${data.window.end}`} />
        </Card>
        <Card>
          <Kpi
            label="Peak compound risk"
            value={fmt(data.peak.score)}
            accent={RISK_COLORS[data.peak.risk_level]}
            sub={
              <span className="flex items-center gap-2">
                <RiskBadge level={data.peak.risk_level} /> {data.peak.date}
              </span>
            }
          />
        </Card>
        <Card>
          <Kpi
            label="Compound detections"
            value={<span className="text-risk-low">{compound?.tp}</span>}
            sub={`${compound?.fp} false positives · ${compound?.alert_days} alert days`}
          />
        </Card>
        <Card>
          <Kpi
            label="Baseline detections"
            value={<span className="text-ink/70">{baseline?.tp}</span>}
            sub={`${baseline?.fp} false positives · ${baseline?.alert_days} alert days`}
          />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Thesis / focus card */}
        <Card dark className="lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="text-gold text-sm font-semibold uppercase tracking-wide">The innovation</div>
            <h2 className="text-2xl font-bold mt-2 leading-snug">
              Compound risk from the <span className="text-gold">interaction</span> of weak signals
            </h2>
            <p className="text-ivory/60 text-sm mt-3 max-w-xl">
              Traditional monitoring watches each signal on its own. EnergyGuardian scores how Brent
              crude, freight rates and corridor events co-elevate — catching multi-signal disruptions a
              per-signal baseline misses, with fewer false alarms.
            </p>
          </div>
          <div className="mt-6 flex flex-wrap gap-6">
            <div>
              <div className="text-3xl font-extrabold tabular text-gold">
                {compound?.tp}<span className="text-ivory/40 text-xl">/{baseline?.tp}</span>
              </div>
              <div className="text-xs text-ivory/50 mt-0.5">compound vs baseline true positives</div>
            </div>
            <div>
              <div className="text-3xl font-extrabold tabular">
                {compound?.fp}<span className="text-ivory/40 text-xl">/{baseline?.fp}</span>
              </div>
              <div className="text-xs text-ivory/50 mt-0.5">compound vs baseline false positives</div>
            </div>
            <div>
              <div className="text-3xl font-extrabold tabular">{fmt(compound?.lead_time_days ?? null, 0)}d</div>
              <div className="text-xs text-ivory/50 mt-0.5">lead time to systemic onset</div>
            </div>
          </div>
        </Card>

        {/* Risk distribution */}
        <Card>
          <SectionTitle title="Risk distribution" subtitle={`${data.n_days} days`} />
          <div className="space-y-4 mt-2">
            {dist.map((d) => (
              <div key={d.name}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="font-semibold" style={{ color: RISK_COLORS[d.name as RiskLevel] }}>
                    {d.name}
                  </span>
                  <span className="tabular text-ink/60">
                    {d.value} <span className="text-ink/35">· {Math.round((d.value / data.n_days) * 100)}%</span>
                  </span>
                </div>
                <div className="h-2.5 rounded-full bg-cream overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(d.value / data.n_days) * 100}%`,
                      backgroundColor: RISK_COLORS[d.name as RiskLevel],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Parameters */}
      <Card>
        <SectionTitle title="Model parameters" subtitle="All assumed; mirrored in the Assumptions page" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <Param label="Weights" value={Object.entries(data.parameters.weights).map(([k, v]) => `${k} ${v}`).join(" · ")} />
          <Param label="λ (interaction)" value={String(data.parameters.lambda)} />
          <Param label="Compound alert ≥" value={String(data.parameters.compound_alert_threshold)} />
          <Param
            label="Risk bounds"
            value={data.parameters.risk_levels
              .filter((r) => r.lower_bound !== null)
              .map((r) => `${r.level} ${r.lower_bound}`)
              .join(" · ")}
          />
        </div>
      </Card>
    </div>
  );
}

function Param({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-cream/60 rounded-2xl px-4 py-3">
      <div className="text-ink/45 text-xs font-medium">{label}</div>
      <div className="font-semibold mt-0.5">{value}</div>
    </div>
  );
}
