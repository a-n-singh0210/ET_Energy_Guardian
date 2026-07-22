# EnergyGuardian AI — 3–4 minute demo video script

**Total runtime: ~3:30.** Left column = what to do on screen. Right/indented = what to say.
Speak at a natural pace; pause at the em-dashes. Have the app open on **Risk Intel** before you hit record, backend + frontend both running (`./run.sh`).

> Tip: rehearse the paste-an-article moment once — that's the "wow" beat. Copy a short real Hormuz/Red Sea news paragraph to your clipboard beforehand (or use the built-in **Load example**).

---

## 0:00 – 0:25 · The hook
**SHOW:** Risk Intel page (the landing view), three corridor gauges visible.

> "India imports 88% of its oil — and nearly half of it sails through one chokepoint: the Strait of Hormuz. When that's threatened, refiners have hours to react and about a nine-day reserve. Today that response is manual and slow. **EnergyGuardian is the layer that fixes that** — it reads the world in real time and turns a news shock into an executable plan in seconds."

---

## 0:25 – 1:10 · Live intelligence + paste-an-article ⭐ (your strongest beat)
**SHOW:** Point at the live corridor scores and the extracted-signals feed. Then scroll to **"Analyze a news article"**, paste a real article (or click **Load example**), click **Extract signal →**.

> "The system already pulls live headlines and scores disruption risk per corridor and per supplier. But here's the part I love — I can paste *any* news article…"
>
> *(paste → click Extract)*
>
> "…and the model reads it and extracts a structured signal — the corridor, the severity, the event type, and how confident it is — with a one-line reason grounded in the text. This isn't a canned demo; it works on articles it's never seen."

**SHOW:** Click **Run through impact model →**.

> "And with one click, I push that signal straight into the impact model."

---

## 1:10 – 1:55 · Command Center — the cascade + the plan
**SHOW:** Command Center loads with the knobs already set from the article. Point to the metric cards (Brent, import gap, GDP), then the **AI decision pipeline** — expand one step (e.g. Scenario Simulation Engine) to show the input → reasoning → output.

> "Now we see the whole cascade — the Brent spike, the import gap, the hit to GDP. Underneath, a five-stage decision pipeline produced the response: which grades to reroute, from where, and how many days the reserve buys us. And I can expand any engine to inspect exactly what went in, how it reasoned, and what came out — nothing is hidden. You can also drag these knobs or load a preset to war-game any scenario live."
>
> *Note: these are honest, deterministic engines — say "decision pipeline," not "AI agents." The one LLM step (news extraction) is on Risk Intel.*

**SHOW:** Drag the Hormuz slider up briefly to show everything recompute.

> "Everything recomputes instantly — signal to recommendation in seconds, not weeks."

---

## 1:55 – 2:25 · Geospatial + Knowledge Graph
**SHOW:** Click **Corridor Map** — point to chokepoints, tanker traffic, reroute lines. Then **Knowledge Graph** — pick a "Hormuz disrupted" preset.

> "On the map, that reroute is physical — supplier origins, real AIS tanker traffic through each chokepoint, and the alternative routes light up. And the knowledge graph shows the dependency structure a flat dashboard can't: disrupt Hormuz and it traces exactly which suppliers are cut off, how much volume is at risk, and which refinery grades are exposed."

---

## 2:25 – 2:55 · The innovation (proof it works)
**SHOW:** Click **Compound vs Baseline**. Point to the two stat pairs (3/2 vs 1/3).

> "Underneath all of this is the core idea: most monitoring watches each signal on its own. We score how weak signals *interact* — because real crises are multi-signal. Validated on the 2023–24 Red Sea crisis, the compound model caught **three times** the events a per-signal baseline did, with fewer false alarms."

---

## 2:55 – 3:20 · Transparency (the trust beat)
**SHOW:** Click **Assumptions** (scroll the table briefly), then **Intelligence Q&A**, type or click a sample question.

> "And none of it is a black box. Every number traces to a documented, editable assumption — the challenge asked for assumptions that are explicit and testable, and here they all are. You can even ask the system a question in plain English and get a sourced answer."

---

## 3:20 – 3:35 · Close
**SHOW:** Return to Risk Intel (or the logo).

> "It's live, it's transparent, it genuinely uses all six suggested technologies — and it runs free, today. That's EnergyGuardian: the response-intelligence layer for import-dependent energy security."

---

## Feature checklist (for your reference — make sure each appears on screen)

| # | Feature | Where | On screen for |
|---|---------|-------|---------------|
| 1 | Live corridor/supplier risk scores | Risk Intel | 0:25 |
| 2 | **Paste-an-article LLM extraction** ⭐ | Risk Intel | 0:35–1:10 |
| 3 | Signal → model one-click bridge | Risk Intel → Command Center | 1:05 |
| 4 | Scenario cascade (Brent / gap / GDP) | Command Center | 1:10 |
| 5 | AI decision pipeline (inspectable input→reasoning→output) + procurement/SPR plan | Command Center | 1:20 |
| 6 | Live knob war-gaming | Command Center | 1:40 |
| 7 | Geospatial map + AIS tanker traffic | Corridor Map | 1:55 |
| 8 | Knowledge graph impact traversal | Knowledge Graph | 2:10 |
| 9 | Compound vs baseline (3× result) | Compound vs Baseline | 2:25 |
| 10 | Assumptions register (transparency) | Assumptions | 2:55 |
| 11 | RAG Q&A | Intelligence Q&A | 3:05 |

**Six technologies to name if asked:** predictive analytics/scenario sim · LLM extraction · orchestrated decision pipeline (agentic pattern, deterministic engines) · knowledge graph · geospatial/AIS · RAG.

**If the LLM path is quota-limited on demo day:** the extractor falls back to transparent keyword rules and still works — but for the cleanest "watch it read this" moment, use a fresh Gemini key so the extraction shows `GEMINI`, not `KEYWORD`.
