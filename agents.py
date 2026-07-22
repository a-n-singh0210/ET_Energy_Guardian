"""agents.py — AI decision pipeline.

Five specialised **engines** run in sequence over a shared context, each reading
what earlier engines wrote, doing one job, and recording an inspectable trace
entry (its inputs, reasoning and output). This powers ``/api/resilience`` — the
dashboard's whole signal→scenario→response flow.

    Signal Interpreter → Scenario Simulation Engine → Procurement Decision Engine
    → Reserve Assessment Engine → Historical Analogue Engine

These are **deterministic** engines, not LLM agents: each is transparent, fast
and recomputable. The one LLM step in the product — extracting structured
disruption signals from news — runs upstream (see ``news_agent.py`` / the Risk
Intel page) and feeds the risk posture this pipeline consumes. Naming them
honestly (engines, not "AI agents") is deliberate.

Engines reuse the existing modules (scenario / procurement / spr / similarity),
so the pipeline adds sequencing and traceability without duplicating logic.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import procurement as proc
import scenario as scen
import similarity as sim
import spr as spr_mod

DISRUPTION_THRESHOLD = 0.15


@dataclass
class Step:
    """One engine's contribution, for the inspectable execution trace."""

    step: int
    name: str
    role: str
    inputs: list[str]
    reasoning: str
    output: str
    decision: str  # one-line summary shown on the collapsed row
    compute_ms: float  # local computation time only (deterministic)
    status: str = "ok"


class Engine:
    """Base engine: reads/writes the shared context, returns a result dict.

    ``run`` returns ``{decision, inputs, reasoning, output}``.
    """

    name = "Engine"
    role = ""

    def run(self, ctx: dict) -> dict:
        raise NotImplementedError


class SignalInterpreter(Engine):
    """Reads the scored risk posture and declares which corridors are compromised."""

    name = "Signal Interpreter"
    role = "Reads the scored risk posture; flags compromised corridors"

    def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        disrupted = []
        if inp["hormuz"] >= DISRUPTION_THRESHOLD:
            disrupted.append("hormuz")
        if inp["redsea"] >= DISRUPTION_THRESHOLD:
            disrupted.append("redsea")
        ctx["disrupted"] = disrupted
        label = ", ".join(disrupted) if disrupted else "none"
        return {
            "decision": f"Corridors compromised: {label}",
            "inputs": [
                f"Hormuz {round(inp['hormuz'] * 100)}%",
                f"Red Sea {round(inp['redsea'] * 100)}%",
                f"OPEC+ cut {inp['opec']} mb/d",
            ],
            "reasoning": (
                f"A corridor is flagged compromised when its disruption level is at or "
                f"above the {round(DISRUPTION_THRESHOLD * 100)}% threshold."
            ),
            "output": f"Compromised corridors → {label}",
        }


class ScenarioEngine(Engine):
    """Simulates the downstream economic cascade of the disruption."""

    name = "Scenario Simulation Engine"
    role = "Simulates Brent, import gap, SPR bridge, GDP & fuel impact"

    def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        s = scen.run_scenario(
            scen.ScenarioInput(inp["hormuz"], inp["redsea"], inp["opec"])
        )
        ctx["scenario"] = s
        return {
            "decision": (
                f"Gap {s['india_import_gap_mbd']} mb/d · Brent +{s['brent_premium_pct']}% "
                f"(${s['brent_price_usd']}) · {s['severity']}"
            ),
            "inputs": [
                f"Compromised: {', '.join(ctx['disrupted']) or 'none'}",
                f"Global supply loss {s['global_supply_loss_mbd']} mb/d",
            ],
            "reasoning": (
                "Supply loss on the compromised corridors maps to India's import gap, "
                "which sets the Brent premium and cascades into GDP, CAD and retail fuel."
            ),
            "output": (
                f"Import gap {s['india_import_gap_mbd']} mb/d · Brent ${s['brent_price_usd']} "
                f"(+{s['brent_premium_pct']}%) · severity {s['severity']}"
            ),
        }


class ProcurementEngine(Engine):
    """Finds and ranks alternative crude sources that avoid disrupted corridors."""

    name = "Procurement Decision Engine"
    role = "Ranks alternative crude sources / routes to close the gap"

    def run(self, ctx: dict) -> dict:
        s = ctx["scenario"]
        gap = float(s["india_import_gap_mbd"])
        result = proc.orchestrate(gap, float(s["brent_price_usd"]), set(ctx["disrupted"]))
        ctx["procurement"] = result
        n_sel = sum(1 for r in result["recommendations"] if r["status"] == "selected")
        if gap <= 1e-6:
            decision = "No gap to backfill"
            output = "No import gap — baseline sourcing holds."
        else:
            decision = (
                f"{result['coverage_pct']}% covered via {n_sel} sources, "
                f"first cargo {result['first_cargo_eta_days']}d @ ${result['blended_landed_usd']}"
            )
            output = (
                f"{result['coverage_pct']}% of the gap covered by {n_sel} compatible sources; "
                f"first cargo in {result['first_cargo_eta_days']} days at "
                f"${result['blended_landed_usd']}/bbl landed."
            )
        return {
            "decision": decision,
            "inputs": [
                f"Gap to close {gap} mb/d",
                f"Avoid corridors: {', '.join(ctx['disrupted']) or 'none'}",
                f"Brent ${s['brent_price_usd']}",
            ],
            "reasoning": (
                "Rank every source that is grade-compatible and reachable without a "
                "compromised corridor, by landed cost and transit time; allocate until "
                "the gap is closed."
            ),
            "output": output,
        }


class ReserveEngine(Engine):
    """Assesses SPR drawdown to bridge the gap until rerouted cargoes arrive."""

    name = "Reserve Assessment Engine"
    role = "Assesses SPR drawdown vs resupply; flags the exposure window"

    def run(self, ctx: dict) -> dict:
        s = ctx["scenario"]
        gap = float(s["india_import_gap_mbd"])
        p = ctx["procurement"]
        result = spr_mod.optimise_drawdown(
            gap, p["first_cargo_eta_days"], float(p["coverage_mbd"])
        )
        ctx["spr"] = result
        spr_days = s.get("spr_bridge_days")
        if result["bridged"]:
            decision = "SPR bridges the gap to resupply"
            output = "Reserve covers the uncovered barrels until rerouted cargoes ramp in."
        else:
            decision = f"Exposure window: {result['exposure_days']} uncovered days"
            output = (
                f"Reserve runs short: {result['exposure_days']} days are uncovered before "
                f"full resupply (day {result['full_resupply_day']})."
            )
        return {
            "decision": decision,
            "inputs": [
                f"Residual gap {p['residual_gap_mbd']} mb/d",
                f"First cargo ETA {p['first_cargo_eta_days']} d",
                f"SPR cover ≈ {spr_days} d" if spr_days else "SPR schedule modelled",
            ],
            "reasoning": (
                "Draw the strategic reserve down to cover uncovered barrels day by day, "
                "then check whether it lasts until rerouted supply fully ramps."
            ),
            "output": output,
        }


class AnalogueEngine(Engine):
    """Retrieves the most similar historical shocks for context."""

    name = "Historical Analogue Engine"
    role = "Matches the posture to past supply shocks (cosine similarity)"

    def run(self, ctx: dict) -> dict:
        s = ctx["scenario"]
        inp = ctx["input"]
        matches = sim.rank_similar(
            float(s["brent_premium_pct"]),
            float(s["global_supply_loss_mbd"]),
            hormuz=inp["hormuz"] > 0,
            redsea=inp["redsea"] > 0,
        )
        ctx["similarity"] = matches
        top = matches[0] if matches else None
        ranked = " · ".join(f"{m['name']} ({m['similarity']})" for m in matches[:4])
        return {
            "decision": f"Closest analogue: {top['name']} ({top['similarity']})" if top else "No analogue",
            "inputs": [
                f"Brent premium +{s['brent_premium_pct']}%",
                f"Supply loss {s['global_supply_loss_mbd']} mb/d",
                f"Corridors: {', '.join(ctx['disrupted']) or 'none'}",
            ],
            "reasoning": (
                "Compare the current posture's structured features against a library of "
                "documented past shocks by cosine similarity, and rank the closest."
            ),
            "output": f"Top analogues → {ranked}" if ranked else "No analogue found",
        }


class Pipeline:
    """Runs the engines in sequence over a shared context and collects the trace."""

    ENGINES = [SignalInterpreter, ScenarioEngine, ProcurementEngine, ReserveEngine, AnalogueEngine]

    def run(self, hormuz: float, redsea: float, opec: float) -> dict:
        """Execute the decision pipeline for one risk posture.

        Args:
            hormuz: Hormuz closure fraction [0, 1].
            redsea: Red Sea suspension fraction [0, 1].
            opec: OPEC+ cut (mb/d).

        Returns:
            The synthesised result (scenario, procurement, spr, similarity,
            disrupted_corridors) plus the inspectable ``pipeline`` trace and
            ``total_compute_ms`` (local computation time only).
        """
        ctx: dict = {"input": {"hormuz": hormuz, "redsea": redsea, "opec": opec}}
        trace: list[Step] = []
        total = 0.0
        for i, engine_cls in enumerate(self.ENGINES, start=1):
            engine = engine_cls()
            t0 = time.perf_counter()
            try:
                res = engine.run(ctx)
                status = "ok"
            except Exception as exc:  # noqa: BLE001 - one engine failing shouldn't kill the run
                res = {"decision": f"failed: {exc}", "inputs": [], "reasoning": "", "output": str(exc)}
                status = "error"
            dt = (time.perf_counter() - t0) * 1000.0
            total += dt
            trace.append(
                Step(
                    step=i, name=engine.name, role=engine.role,
                    inputs=res.get("inputs", []), reasoning=res.get("reasoning", ""),
                    output=res.get("output", ""), decision=res.get("decision", ""),
                    compute_ms=round(dt, 2), status=status,
                )
            )

        return {
            "scenario": ctx.get("scenario"),
            "procurement": ctx.get("procurement"),
            "spr": ctx.get("spr"),
            "similarity": ctx.get("similarity"),
            "disrupted_corridors": ctx.get("disrupted", []),
            "pipeline": [asdict(t) for t in trace],
            "total_compute_ms": round(total, 2),
        }


def orchestrate(hormuz: float, redsea: float, opec: float) -> dict:
    """Convenience wrapper around :class:`Pipeline`."""
    return Pipeline().run(hormuz, redsea, opec)


if __name__ == "__main__":
    out = orchestrate(0.6, 0.3, 1.0)
    print(f"Total local compute: {out['total_compute_ms']} ms")
    for t in out["pipeline"]:
        print(f"  [{t['compute_ms']:>6} ms] {t['name']:28} → {t['decision']}")
