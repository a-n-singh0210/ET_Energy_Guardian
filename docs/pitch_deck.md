# EnergyGuardian AI — Pitch Deck

**AI-Driven Energy Supply Chain Resilience for Import-Dependent Economies**

> 12 slides. Each has the on-slide content and a speaker note. Judging weights
> are called out so every slide is earning its place:
> Innovation 25 · Business Impact 25 · Technical Excellence 20 · Scalability 15 · UX 15.

---

### Slide 1 — Title
**EnergyGuardian AI** — Turning energy-supply crises from reactive to anticipatory.
*Team · Economic Times Hackathon · Energy Security / Geopolitical Risk*

> Speaker: "India imports 88% of its crude, and 40–45% of it goes through one
> chokepoint — the Strait of Hormuz. We built the intelligence layer that tells
> India what to do when that chokepoint is threatened — in seconds, not weeks."

---

### Slide 2 — The problem (make it visceral) · Business Impact
- 88% import dependence · 40–45% via Hormuz.
- 2025 US–Iran standoff: Brent +8% in one session; refiners forced onto spot at premiums.
- SPR = **~9.5 days** of cover. McKinsey: economies without automated rerouting take **+47 days** longer to stabilise.
- Traditional tools can't model geopolitical scenarios, evaluate corridors, or orchestrate response.

> Speaker: "This isn't hypothetical — it's a structural vulnerability that gets
> stress-tested every few months. The gap isn't data; it's the decision layer."

---

### Slide 3 — What we built (one line + the loop) · Innovation
> **A live signal → scenario → executable-response loop.**
- Show the architecture diagram (docs/architecture.html).
- Live news + market signals → risk intelligence agent → resilience engines → decision cockpit.

> Speaker: "One system, one loop. It watches the world, models the shock, and
> hands a procurement team a plan they can act on."

---

### Slide 4 — Live demo entry: Risk Intelligence Agent · Innovation + UX
- Screenshot the **Risk Intel** page: 45 live headlines ingested now.
- Per-corridor disruption probability (Hormuz / Red Sea / Global) + per-supplier board.
- LLM extraction (Gemini) turns each headline into a structured event.

> Speaker: "This is live — real headlines pulled seconds ago. An LLM reads each
> one and scores disruption probability by corridor *and* by supplier. Updated
> continuously, not weekly."

---

### Slide 5 — Scenario Modeller · Business Impact + Technical Excellence
- Command Center: drag Hormuz → 60%, Red Sea → 30%.
- Live cascade: Brent +136% → $189, gap 1.52 mb/d, SPR bridge 14d, GDP −2.83pp, fuel +68%.
- Numbered reasoning chain — every number traceable.

> Speaker: "Every figure is a transparent function of documented assumptions —
> we can show the judges the exact arithmetic. No black box."

---

### Slide 6 — Refinery + GDP trajectory · Business Impact
- Refinery run-rate at risk: 72%.
- GDP trajectory: **managed vs reactive** — the McKinsey 47-day gap, quantified as a recovery curve.

> Speaker: "This is the money slide. Without a response system, the economy
> bleeds growth for months longer. That delta is what EnergyGuardian buys back."

---

### Slide 7 — Adaptive Procurement Orchestrator · Business Impact
- Given the 1.52 mb/d gap, orchestrator ranks alternatives, avoids disrupted corridors.
- Output: 100% coverage via 7 Atlantic/Cape sources, blended $188/bbl, first cargo 22d — executable.

> Speaker: "This is what a procurement team acts on within hours: which grades,
> how much, which route, what it lands at, when it arrives."

---

### Slide 8 — SPR Optimiser + the exposure gap · Business Impact
- SPR bridges to ~day 14; first resupply day 22; ramp to day 32.
- Verdict: exposure window → recommend demand curtailment / shorter-haul lifting.

> Speaker: "The system doesn't just say 'reroute' — it tells the policymaker the
> reserve won't fully bridge to resupply, and by how much. That's decision support."

---

### Slide 9 — Corridor Map · UX + geospatial evidence
- Geospatial map: disrupted chokepoints red, resilient Atlantic/Cape reroutes green to India.

> Speaker: "The reroute isn't abstract — here's the physical corridor shift, live
> under the active scenario."

---

### Slide 10 — Why trust it: validated detection · Technical Excellence
- Compound interaction model back-tested on real 2023–24 Red Sea data.
- vs independent baseline: **3× the true detections with fewer false positives**.
- Historical similarity: current posture ≈ Gulf War 1990 (0.91), Russia 2022 (0.97).

> Speaker: "Our detection edge is measured, not claimed — on real historical data,
> against a fair baseline."

---

### Slide 11 — Architecture & scalability · Technical Excellence + Scalability
- Show architecture diagram. Stateless Flask API, modular engines, cached live feed.
- Free to run: live news + Gemini free tier + open data — no paid feeds.
- Scales to more corridors, suppliers, commodities.

> Speaker: "Clean separation: agent, engines, API, UI. Add a corridor or a
> commodity without touching the core. And it costs nothing to run."

---

### Slide 12 — The ask / close · Innovation + Business Impact
- From reactive to anticipatory: signal → recommendation in seconds.
- Transparent, validated, live, free.
- Next: real AIS vessel tracking, sanctions registry RAG, multi-commodity.

> Speaker: "EnergyGuardian turns a 47-day scramble into a same-day plan — with
> every assumption on the table. That's the intelligence layer India's energy
> security needs."

---

## Judging-criteria coverage map

| Criterion | Weight | Where we win it |
|---|---|---|
| Innovation | 25% | Live LLM risk agent + compound-interaction detection + anticipatory loop |
| Business Impact | 25% | Executable procurement + SPR bridge + GDP-trajectory delta (47-day stat) |
| Technical Excellence | 20% | Validated detection vs baseline; fully transparent, testable assumptions |
| Scalability | 15% | Stateless API, modular engines, free data, multi-corridor design |
| User Experience | 15% | One-click signal→response; polished interactive cockpit + map |

## Positioning (say this, beat every over-claiming team)
"Most 'AI' entries are a black box you have to trust. Ours shows its work — every
scenario number traces to a documented, editable assumption, and our detection
edge is measured on real data. Live where live matters (news, prices), transparent
where transparency matters (impact models)."
