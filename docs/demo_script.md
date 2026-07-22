# EnergyGuardian AI — Demo Video Script (3 minutes)

> Goal: show the **live signal → scenario → executable response** loop end to
> end, and land the transparency differentiator. Timings are targets.
> Pre-flight: run `python api.py` and `npm run dev`; set `GEMINI_API_KEY` so the
> Risk Intel page shows "GEMINI" extraction; open on the **Risk Intel** tab.

---

**[0:00–0:20] Hook**
> "India imports 88% of its crude — and nearly half of it passes through a single
> chokepoint, the Strait of Hormuz. When that's threatened, refiners have hours to
> react and a 9.5-day reserve. Today, that response is manual and slow.
> EnergyGuardian makes it instant."

*On screen: Risk Intel page, already loaded with live headlines.*

---

**[0:20–0:55] Live intelligence** *(Innovation + "continuous")*
> "This is live. The agent just pulled real headlines and — using an LLM — scored
> disruption probability by corridor and by supplier."

- Point to Hormuz / Red Sea gauges. Click **↻ Refresh feed** — timestamp updates.
- Scroll the extracted-signals feed: "Each headline becomes a structured event —
  corridor, supplier, severity, confidence."

---

**[0:55–1:30] One-click signal → scenario** *(the loop + Business Impact)*
> "Now watch the anticipatory loop. One click carries the current live risk into
> the impact model."

- Click **Simulate current risk →**. Lands on Command Center, knobs pre-set.
- "Instantly: Brent premium, import gap, SPR bridge, GDP hit, fuel impact — and
  the exact reasoning behind every number."
- Point to the numbered cascade: "This is transparent — no black box."

---

**[1:30–2:00] Impact + the 47-day story** *(Business Impact)*
- Point to **Refinery run-rate at risk** and the **GDP trajectory** chart.
> "Without a response system, McKinsey found economies take 47 days longer to
> stabilise. That's this red curve — months of lost growth. The green curve is
> the managed path. That gap is what we buy back."

---

**[2:00–2:35] Executable recommendation** *(Business Impact + "executable")*
- Scroll to **Adaptive procurement**.
> "Here's what a procurement team acts on within hours: rerouted crude sources,
> avoiding the disrupted corridors — grades, volumes, landed cost, and arrival
> dates. 100% of the gap covered via Atlantic and Cape routes."
- Click **Corridor Map**: "And here's the physical reroute — red is blocked,
  green is the resilient path to India."

---

**[2:35–2:55] Why trust it** *(Technical Excellence)*
- Click **Compound vs Baseline**.
> "Our detection isn't a claim — it's validated on real 2023–24 Red Sea data,
> beating an independent baseline 3-to-1 on true detections with fewer false
> alarms. And every assumption is documented and editable."

---

**[2:55–3:00] Close**
> "Live where it matters, transparent where it matters. Signal to recommendation
> in seconds. That's EnergyGuardian."

*On screen: architecture diagram or title card.*

---

## Recording tips
- Record at 1440-wide; the layout is designed for it.
- Have the scenario pre-set to **Hormuz major + OPEC+** as a fallback if live news is quiet.
- If `GEMINI_API_KEY` isn't set, the agent still runs (keyword mode) — but set it so the demo shows real LLM extraction.
- Keep the cursor deliberate; pause 1s on each KPI so viewers can read it.
