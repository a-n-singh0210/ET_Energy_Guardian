import { useState } from "react";
import { api, type Ask } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle } from "../components/ui";

export default function AskIntel() {
  const samples = useApi(api.askSamples);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const result = useApi<Ask | null>(
    () => (submitted ? api.ask(submitted) : Promise.resolve(null)),
    [submitted]
  );

  const run = (q: string) => { setQuery(q); setSubmitted(q); };

  return (
    <div className="space-y-5">
      <Card>
        <SectionTitle
          title="Intelligence Q&A"
          subtitle="Retrieval-augmented answers grounded in a cited geopolitical & commodity corpus"
        />
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && query.trim()) run(query.trim()); }}
            placeholder="Ask about Hormuz, SPR, alternative crude, price shocks…"
            className="flex-1 bg-cream rounded-xl px-4 py-3 text-sm outline-none"
          />
          <button
            onClick={() => query.trim() && run(query.trim())}
            className="px-5 py-3 rounded-xl font-semibold bg-ink text-ivory hover:opacity-90"
          >
            Ask
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {(samples.data?.samples ?? []).map((s) => (
            <button key={s} onClick={() => run(s)}
              className="text-xs px-3 py-1.5 rounded-full bg-cream/70 hover:bg-sand text-ink/70">
              {s}
            </button>
          ))}
        </div>
      </Card>

      {submitted && result.loading && <Loading />}
      {result.error && <ErrorState message={result.error} />}
      {result.data && (
        <>
          <Card dark>
            <div className="flex items-center justify-between mb-2">
              <div className="text-gold text-sm font-semibold uppercase tracking-wide">Grounded answer</div>
              <span className="text-[10px] font-mono text-ivory/40 border border-ivory/20 rounded px-2 py-0.5">
                {result.data.retrieval === "gemini" ? "dense vector RAG · Gemini" : "TF-IDF retrieval"}
                {result.data.generated ? " + generation" : " (retrieval only)"}
              </span>
            </div>
            {result.data.answer ? (
              <p className="text-ivory/90 text-[15px] leading-relaxed">{result.data.answer}</p>
            ) : (
              <p className="text-ivory/70 text-sm">Retrieval-only mode (no LLM key). The most relevant sourced passages are below.</p>
            )}
          </Card>

          <Card>
            <SectionTitle title="Retrieved sources" subtitle="Ranked by semantic similarity — the answer is grounded only in these" />
            <div className="space-y-2.5">
              {result.data.sources.map((s) => (
                <div key={s.id} className="bg-cream/50 rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-ink text-ivory">[{s.id}]</span>
                    {s.score != null && <span className="text-xs text-ink/40">similarity {s.score}</span>}
                    <span className="text-xs text-ink/40 ml-auto">source: {s.source}</span>
                  </div>
                  <div className="text-sm text-ink/80 leading-snug">{s.text}</div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
