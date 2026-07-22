# Lovable prompt — EnergyGuardian AI dashboard

> Paste everything below the line into Lovable. It builds a React frontend that
> talks to the local Flask API (`v2/api.py`) running at `http://localhost:5001`.
> All numbers come from the API — the frontend must never compute risk itself.

---

Build a polished, dark, data-dense **risk-intelligence dashboard** called
**EnergyGuardian AI**. It visualizes a compound supply-chain risk model for the
2023–24 Red Sea shipping crisis. It is a read-only analytics UI over an existing
JSON API — do all rendering in the frontend, but perform **no calculations**;
every value comes from the API exactly as returned.

## Product thesis (show this framing in the UI copy)

Traditional monitoring watches each signal independently. EnergyGuardian scores
how *weak signals interact*: the innovation is a compound risk score
`Risk = Σ wᵢaᵢ + λ Σ aᵢ⁺aⱼ⁺` that rewards **co-elevation** of heterogeneous
disruption signals (Brent crude, freight rates, corridor events). The headline
story: the compound model catches multi-signal disruptions a per-signal baseline
misses, with fewer false alarms.

## Tech & configuration

- React + Vite + TypeScript, Tailwind, shadcn/ui components, **Recharts** for charts.
- API base URL from `import.meta.env.VITE_API_URL`, defaulting to
  `http://localhost:5001`. Put all fetch calls in a small `src/lib/api.ts` client.
- Show a loading skeleton while fetching and a clear error state if the API is
  unreachable (tell the user to run `python api.py`).
- Fully responsive; looks great on a laptop.

## Design system

- **Theme:** dark, professional, "mission-control" feel. Deep slate background
  (#0B1220 / #0F172A), card surfaces (#111A2E) with subtle borders (#1E293B).
- **Accent:** a confident blue (#3B82F6) for primary/series lines.
- **Risk-level colors (use consistently everywhere a risk level appears):**
  LOW = #22C55E, MODERATE = #EAB308, HIGH = #F97316, SEVERE = #EF4444.
- Typography: clean sans (Inter). Generous spacing, rounded-xl cards, soft
  shadows. Numbers in a tabular/mono style for alignment.
- Layout: left sidebar nav (icon + label) with the six sections below; a slim
  top bar with the product name and the analysis window (from `/api/overview`).

## Sections (sidebar navigation)

### 1. Overview  — `GET /api/overview`
- KPI cards: Days analysed (`n_days`), Peak risk (`peak.score` + colored
  `peak.risk_level` badge + `peak.date`), and a compact comparison callout
  ("Compound: 3 TP / 2 FP vs Baseline: 1 TP / 3 FP" from `comparison`).
- A risk-distribution donut/bar from `risk_distribution` using the risk colors.
- A "Model parameters" card from `parameters` (weights, λ, risk-level bounds,
  baseline thresholds) — presented as a clean key/value table.

### 2. Timeline — `GET /api/timeline`
- A full-width line chart of `score_series` (`compound_score` over `date`), with
  colored horizontal reference lines at the risk-level bounds (from overview
  `parameters.risk_levels`, skip null bound).
- Below it, a timeline/table of `events` (date, event, category chip, severity
  as 1–5 dots or a small bar). Sort ascending by date.

### 3. Signals — `GET /api/signals`
- A multi-line chart of `anomalies` with three series: `anomaly_brent`,
  `anomaly_freight`, `anomaly_events` (y-range roughly [-3, 3], zero baseline).
- A secondary chart of `features` (`brent_return`, `event_severity_14`, and
  `freight_wci_ffill` on its own axis/scale — freight is a large USD level).
- Caption: "Anomaly scores are robust z-scores over a 14-day window, clipped to
  [-3, 3]."

### 4. Compound vs Baseline — `GET /api/compare`
- The hero comparison. Line chart of the compound score over time (reuse
  `/api/compound` `series.compound_score`, or fetch it) with:
  - hollow circle markers on `compound_alert_dates`,
  - downward-triangle markers on `baseline_alert_dates`,
  - dashed vertical lines on `gt_events`,
  - a solid vertical line on `systemic_onset`,
  - a dashed horizontal line at `compound_alert_threshold`.
- A comparison table from `comparison` (method, alert_days, lead_time_days, tp,
  fn, fp) — highlight that compound has more TP and fewer FP.
- A threshold-sensitivity chart from `sensitivity` (x = threshold; lines for tp,
  fp, fn, alert_days).

### 5. Explanation — `GET /api/explanation/dates` then `GET /api/explanation?date=…`
- A date picker/dropdown populated from `dates`, defaulting to `default`.
- Render the returned `text` as a clean, readable "explanation card" and show a
  colored `risk_level` badge (derive from `trace.final.risk_level`).
- An expandable "Audit trail" panel visualizing `trace` as the chain:
  **raw signals → anomaly scores → linear contributions → interaction
  contributions → final score**. Use small labeled stat rows / a horizontal
  stepper. The explanation text is a fully deterministic template.

### 6. Assumptions — `GET /api/assumptions`
- Render the returned `markdown` field with a markdown renderer (tables, headers)
  inside a readable card. This is the credibility/"show your work" page.

Optionally add a **Replay** control on the Timeline or Overview: a slider over
the dates that reveals the compound score line progressively up to the selected
day and shows that day's risk badge — purely a view of already-fetched data.

## Behavior rules

- Never compute or transform risk numbers client-side; only format them (rounding,
  date formatting, color mapping). The API is the source of truth.
- `lead_time_days` may be `null` (no lead) — render as "—".
- Some series values are `null` (e.g. Brent on weekends) — Recharts should gap,
  not interpolate.
- Keep copy factual and understated (the model is honest about limitations).

## API contract (all GET, JSON, base `http://localhost:5001`)

`/api/overview`
```json
{
  "window": {"start": "2023-10-02", "end": "2024-03-31"},
  "n_days": 183,
  "peak": {"date": "2023-12-20", "score": 3.272, "risk_level": "HIGH"},
  "risk_distribution": {"LOW": 156, "MODERATE": 22, "HIGH": 5},
  "comparison": [
    {"method": "baseline", "alert_days": 4, "lead_time_days": 7.0, "tp": 1, "fn": 9, "fp": 3},
    {"method": "compound", "alert_days": 5, "lead_time_days": 7.0, "tp": 3, "fn": 7, "fp": 2}
  ],
  "signals": [{"key": "brent", "label": "Brent crude", "role": "Market-stress context"}, ...],
  "parameters": {
    "weights": {"brent": 1.0, "freight": 1.0, "events": 1.0},
    "lambda": 1.5,
    "risk_levels": [{"level": "LOW", "lower_bound": null}, {"level": "MODERATE", "lower_bound": 1.0}, {"level": "HIGH", "lower_bound": 2.5}, {"level": "SEVERE", "lower_bound": 4.0}],
    "baseline_thresholds": {"brent": 2.0, "freight": 2.0, "events": 2.0},
    "compound_alert_threshold": 2.5
  }
}
```

`/api/timeline`
```json
{
  "events": [{"date": "2023-11-19", "event": "Houthi forces seize the car carrier Galaxy Leader ...", "category": "seizure", "severity": 3}, ...],
  "score_series": [{"date": "2023-10-02", "compound_score": 0.0, "risk_level": "LOW"}, ...]
}
```

`/api/signals`
```json
{
  "anomalies": [{"date": "2023-12-20", "anomaly_brent": 0.239, "anomaly_freight": 0.674, "anomaly_events": 2.023}, ...],
  "features": [{"date": "2023-12-20", "brent_return": 0.006, "freight_wci_ffill": 1521.0, "event_severity_14": 14.0}, ...]
}
```

`/api/compound`
```json
{
  "series": [{
    "date": "2023-12-20",
    "signal_brent": 0.239, "signal_freight": 0.674, "signal_events": 2.023,
    "int_brent__freight": 0.027, "int_brent__events": 0.081, "int_freight__events": 0.227,
    "linear_total": 2.937, "interaction_total": 0.335,
    "compound_score": 3.272, "risk_level": "HIGH"
  }, ...]
}
```

`/api/compare`
```json
{
  "comparison": [{"method": "baseline", "alert_days": 4, "lead_time_days": 7.0, "tp": 1, "fn": 9, "fp": 3}, {"method": "compound", ...}],
  "compound_alert_dates": ["2023-12-08", "2023-12-20", "2023-12-26", "2024-01-18", "2024-01-25"],
  "baseline_alert_dates": ["2023-12-08", "2023-12-20", "2024-03-13", "2024-03-18"],
  "gt_events": ["2023-12-03", "2023-12-14", ...],
  "systemic_onset": "2023-12-15",
  "compound_alert_threshold": 2.5,
  "sensitivity": [{"threshold": 1.0, "alert_days": 27, "tp": 6, "fn": 4, "fp": 17, "lead_time_days": 28.0}, ...]
}
```

`/api/explanation/dates`
```json
{"dates": ["2023-10-02", ...], "default": "2023-12-20"}
```

`/api/explanation?date=2023-12-20`
```json
{
  "date": "2023-12-20",
  "text": "[2023-12-20] Risk level: HIGH (compound score 3.272). Raw signals — ...",
  "trace": {
    "raw": {"brent_return": 0.006, "freight_wci_ffill": 1521.0, "event_severity_14": 14.0, "n_events": 0, "events_text": ""},
    "anomalies": {"brent": 0.239, "freight": 0.674, "events": 2.023},
    "linear_contributions": {"brent": 0.239, "freight": 0.674, "events": 2.023},
    "interaction_contributions": {"brentxfreight": 0.027, "brentxevents": 0.081, "freightxevents": 0.227},
    "final": {"linear_total": 2.937, "interaction_total": 0.335, "compound_score": 3.272, "risk_level": "HIGH"}
  }
}
```

`/api/assumptions`
```json
{"markdown": "# Assumptions Register\n\n..."}
```
