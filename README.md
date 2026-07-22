# EnergyGuardian AI

**A live, explainable early-warning and response system for import-dependent
energy economies — built around India and the Strait of Hormuz.**

India imports ~88% of its crude, and nearly half of it transits one chokepoint.
When that lane is threatened, the response today is manual and slow.
EnergyGuardian reads live news and market signals, scores disruption risk by
**corridor and supplier** in real time, and — in one click — simulates the shock
end to end and produces an **executable** procurement-reroute and reserve-drawdown
plan. Signal to recommendation in seconds.

Every number is transparent and traces to a documented, editable assumption.
The only LLM use is extracting structured signals from news — never computing a
risk number, and never wording the explanations, which are fully deterministic
templates.

## What it does

- **Risk Intel** — live per-corridor / per-supplier risk from news, plus a
  *paste-an-article* box: paste any report and the LLM extracts the disruption
  signal, then runs it through the impact model.
- **Command Center** — a scenario modeller (Hormuz / Red Sea / OPEC+ knobs) whose
  full cascade (Brent, import gap, refinery run-rate, GDP) updates live, driven by
  an inspectable **AI decision pipeline** (five deterministic engines → procurement
  + reserve plan, each step's input → reasoning → output expandable).
- **Corridor Map** — supplier → chokepoint → India geography with AIS-derived
  tanker traffic and scenario-driven reroute highlighting.
- **Knowledge Graph** — supplier ↔ corridor ↔ grade ↔ refinery graph with
  impact-by-traversal queries.
- **Intelligence Q&A** — retrieval-augmented, cited answers over an
  energy-security corpus.
- **Detection model** — the core compound-risk engine (Detection · Timeline ·
  Signals · Compound vs Baseline · Explanation · Assumptions), validated on the
  2023–24 Red Sea crisis.

## The compound model

For each day, robust z-score anomalies (median/MAD, 14-day window, clipped
[-3, 3]) are combined:

```
Risk(t) = Σ wᵢ·aᵢ(t)  +  λ Σ aᵢ⁺(t)·aⱼ⁺(t)
          └ signed linear ┘   └ co-elevation interaction ┘
```

The interaction term — which only fires when signals are *simultaneously*
elevated — is the innovation. Validated Oct 2023–Mar 2024 against 10 documented
events, the compound model caught 3× the events of a per-signal baseline with
fewer false alarms.

## Run it

One command starts the Flask API and the React dashboard together:

```bash
./run.sh                 # API on :5001 · dashboard on :5173
```

Or run them separately:

```bash
# backend (Python 3.11)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python api.py            # http://localhost:5001

# frontend
cd frontend && npm install
npm run dev              # http://localhost:5173
```

### Optional: live LLM extraction (free)

Set a free Google AI Studio key for real LLM news extraction; without it the
system falls back to a transparent keyword classifier and still runs.

```bash
export GEMINI_API_KEY=...   # free tier — aistudio.google.com
```

## Stack

Python (pandas · numpy · scikit-learn · networkx · Flask) backend; React +
TypeScript + Vite + Tailwind + Recharts + d3-geo frontend. The frontend is
display-only — every risk number is computed in the backend.

## Documentation

See [`docs/`](docs/) for the assumptions register, data sources, architecture
diagram, pitch deck, submission document, and demo script.
