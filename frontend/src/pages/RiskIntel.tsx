import { useState } from "react";
import { api, type ExtractResult } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle } from "../components/ui";

const CORRIDOR_LABEL: Record<string, string> = {
  hormuz: "Strait of Hormuz",
  redsea: "Red Sea / Bab-el-Mandeb",
  global: "Global (OPEC+/sanctions)",
  none: "No corridor",
};

const EXAMPLE_ARTICLE =
  "DUBAI — Tensions in the Persian Gulf escalated sharply on Tuesday after two oil tankers " +
  "were seized near the Strait of Hormuz, with naval forces reporting drone activity in the " +
  "shipping lane. Several shipping firms said they were temporarily rerouting vessels away " +
  "from the strait, through which roughly a fifth of the world's seaborne oil passes. Brent " +
  "crude jumped more than 4% on the news. Analysts warned that a sustained disruption to " +
  "Hormuz transit could remove significant crude volumes from global markets.";

function riskColor(p: number): string {
  if (p >= 0.75) return "#DC3545";
  if (p >= 0.5) return "#E8730C";
  if (p >= 0.25) return "#E0A92E";
  return "#22A06B";
}

export default function RiskIntel({ onSimulate }: { onSimulate: (h: number, r: number, o: number) => void }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading } = useApi(() => api.intel(refreshKey > 0), [refreshKey]);

  // Paste-an-article extraction state.
  const [text, setText] = useState("");
  const [xr, setXr] = useState<ExtractResult | null>(null);
  const [xLoading, setXLoading] = useState(false);
  const [xErr, setXErr] = useState<string | null>(null);

  const runExtract = async () => {
    setXLoading(true);
    setXErr(null);
    setXr(null);
    try {
      const res = await api.extractArticle(text);
      if (!res.ok) setXErr(res.error ?? "extraction failed");
      else setXr(res);
    } catch (e) {
      setXErr(e instanceof Error ? e.message : "extraction failed");
    } finally {
      setXLoading(false);
    }
  };

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "no intel"} />;

  const cs = data.corridor_scores;
  const suggested = {
    h: cs.hormuz ?? 0,
    r: cs.redsea ?? 0,
    o: (cs.global ?? 0) > 0.4 ? 1 : 0,
  };

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionTitle
            title="Live geopolitical risk intelligence"
            subtitle={`Ingested ${data.headline_count} live headlines · extraction: ${data.method.toUpperCase()} · updated ${new Date(data.generated_at).toLocaleString()}`}
          />
          <button
            onClick={() => setRefreshKey((k) => k + 1)}
            className="px-4 py-2 rounded-full text-sm font-semibold bg-ink text-ivory hover:opacity-90"
          >
            ↻ Refresh feed
          </button>
        </div>
        <div className="text-xs text-ink/40 mt-1">
          Source: Google News RSS (live) → {data.method === "gemini" ? "Gemini LLM extraction" : "keyword extraction (set GEMINI_API_KEY — free — for LLM)"}. Scores are recency-weighted severity × confidence.
        </div>
      </Card>

      {/* Paste-an-article extraction */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SectionTitle
            title="Analyze a news article"
            subtitle="Paste any report — the LLM extracts the disruption signal, then runs it through the impact model"
          />
          <button
            onClick={() => setText(EXAMPLE_ARTICLE)}
            className="text-xs font-semibold text-ink/45 hover:text-ink underline underline-offset-2"
          >
            Load example
          </button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="Paste a Reuters / Bloomberg / news article here…"
          className="w-full mt-3 rounded-2xl bg-cream/50 border border-black/5 px-4 py-3 text-sm leading-relaxed resize-y outline-none focus:border-goldDeep/50 focus:bg-white/60 transition"
        />

        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={runExtract}
            disabled={xLoading || text.trim().length === 0}
            className="px-5 py-2.5 rounded-full font-bold bg-ink text-ivory hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {xLoading ? "Reading article…" : "Extract signal →"}
          </button>
          {xErr && <span className="text-sm text-risk-severe font-medium">{xErr}</span>}
        </div>

        {xr && (
          <div className="mt-4 rounded-2xl border border-black/5 bg-white/50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-goldDeep">
                Extracted signal
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full bg-cream text-ink/50">
                {xr.method}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Corridor", value: CORRIDOR_LABEL[xr.corridor] ?? xr.corridor },
                { label: "Event type", value: xr.event_type },
                { label: "Severity", value: `${xr.severity} / 5`, color: riskColor(xr.severity / 5) },
                { label: "Confidence", value: `${Math.round(xr.confidence * 100)}%` },
              ].map((f) => (
                <div key={f.label} className="rounded-xl bg-cream/50 px-3 py-2.5">
                  <div className="text-[11px] text-ink/45 font-medium">{f.label}</div>
                  <div
                    className="text-lg font-extrabold leading-tight mt-0.5"
                    style={f.color ? { color: f.color } : undefined}
                  >
                    {f.value}
                  </div>
                </div>
              ))}
            </div>

            {xr.rationale && (
              <p className="text-sm text-ink/55 mt-3 leading-snug">
                <span className="font-semibold text-ink/70">Why:</span> {xr.rationale}
              </p>
            )}

            {xr.supplier !== "none" && (
              <p className="text-xs text-ink/40 mt-1">Supplier implicated: {xr.supplier}</p>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 mt-4 pt-3 border-t border-black/5">
              <div className="text-xs text-ink/45">
                Maps to knobs · Hormuz {Math.round(xr.suggested_knobs.h * 100)}% · Red Sea{" "}
                {Math.round(xr.suggested_knobs.r * 100)}% · OPEC+ {xr.suggested_knobs.o.toFixed(1)} mb/d
              </div>
              <button
                onClick={() =>
                  onSimulate(xr.suggested_knobs.h, xr.suggested_knobs.r, xr.suggested_knobs.o)
                }
                className="px-5 py-2.5 rounded-full font-bold bg-gold text-ink hover:opacity-90 whitespace-nowrap"
              >
                Run through impact model →
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Corridor risk gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {(["hormuz", "redsea", "global"] as const).map((c) => {
          const p = cs[c] ?? 0;
          return (
            <Card key={c}>
              <div className="text-sm text-ink/50 font-medium">{CORRIDOR_LABEL[c]}</div>
              <div className="flex items-end gap-2 mt-1">
                <div className="text-4xl font-extrabold tabular" style={{ color: riskColor(p) }}>
                  {Math.round(p * 100)}
                </div>
                <div className="text-ink/40 mb-1.5 text-sm">/ 100 disruption probability</div>
              </div>
              <div className="h-2.5 rounded-full bg-cream overflow-hidden mt-2">
                <div className="h-full rounded-full" style={{ width: `${p * 100}%`, backgroundColor: riskColor(p) }} />
              </div>
            </Card>
          );
        })}
      </div>

      {/* Signal → response bridge */}
      <Card dark className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-gold text-sm font-semibold uppercase tracking-wide">Anticipatory response</div>
          <p className="text-ivory/80 text-sm mt-1 max-w-2xl">
            The agent detects elevated corridor risk from live news. Run the current risk posture through the
            impact model to get an executable procurement recommendation in seconds — signal → scenario → response.
          </p>
        </div>
        <button
          onClick={() => onSimulate(suggested.h, suggested.r, suggested.o)}
          className="px-5 py-3 rounded-full font-bold bg-gold text-ink hover:opacity-90 whitespace-nowrap"
        >
          Simulate current risk →
        </button>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Supplier risk board */}
        <Card>
          <SectionTitle title="Supplier risk board" subtitle="Probability by import source" />
          <div className="space-y-2.5">
            {Object.entries(data.supplier_scores)
              .sort((a, b) => b[1] - a[1])
              .map(([name, p]) => (
                <div key={name} className="flex items-center gap-3">
                  <div className="w-32 text-sm font-medium shrink-0">{name}</div>
                  <div className="flex-1 h-2.5 rounded-full bg-cream overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${p * 100}%`, backgroundColor: riskColor(p) }} />
                  </div>
                  <div className="w-10 text-right text-sm font-bold tabular" style={{ color: riskColor(p) }}>{Math.round(p * 100)}</div>
                </div>
              ))}
          </div>
        </Card>

        {/* Live event feed */}
        <Card>
          <SectionTitle title="Extracted disruption signals" subtitle="Structured events from live headlines" />
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {data.top_events.map((e, i) => (
              <div key={i} className="bg-cream/50 rounded-2xl px-4 py-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full text-white" style={{ backgroundColor: riskColor(e.severity / 5) }}>
                    sev {e.severity}
                  </span>
                  <span className="text-xs font-semibold text-ink/50 uppercase">{e.corridor}</span>
                  {e.supplier !== "none" && <span className="text-xs text-ink/40">· {e.supplier}</span>}
                  <span className="text-xs text-ink/30 ml-auto">conf {e.confidence.toFixed(2)}</span>
                </div>
                <div className="text-sm leading-snug">{e.title}</div>
                <div className="text-xs text-ink/35 mt-0.5">{e.source}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
