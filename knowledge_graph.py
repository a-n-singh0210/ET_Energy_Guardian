"""knowledge_graph.py — supplier ↔ corridor ↔ grade ↔ refinery knowledge graph.

Builds a real directed knowledge graph (with ``networkx``) of the relationships
that matter for supply resilience:

    Supplier  --ships_via-->  Corridor  --delivers_to-->  Refinery
    Supplier  --produces-->   Grade     --compatible_with--> Refinery

The graph powers relationship queries the tabular data can't answer directly —
most importantly the **impact query**: given a set of disrupted corridors, which
suppliers are cut off, which grades are at risk, and how much volume is exposed
(graph traversal, not a hand-coded lookup).
"""

from __future__ import annotations

import networkx as nx

import india_params as P
import procurement as proc

# Indian refineries and the crude grades they can run (assumption; Jamnagar is a
# high-complexity refinery that handles heavy sour well).
REFINERIES = {
    "Jamnagar/Sikka": ["light sweet", "medium sweet", "medium sour", "heavy sour"],
    "Paradip": ["medium sour", "heavy sour", "medium sweet"],
}
CORRIDOR_LABEL = {
    "hormuz": "Strait of Hormuz",
    "redsea": "Red Sea / Suez",
    "atlantic_cape": "Atlantic / Cape",
}


def build_graph() -> nx.DiGraph:
    """Construct the knowledge graph from the procurement source model.

    Returns:
        A ``networkx.DiGraph`` with typed nodes (supplier / corridor / grade /
        refinery) and typed edges (ships_via / produces / delivers_to /
        compatible_with). Supplier nodes carry their spare volume; corridors and
        grades are shared hubs.
    """
    g = nx.DiGraph()

    for corridor, label in CORRIDOR_LABEL.items():
        g.add_node(f"corridor:{corridor}", label=label, kind="corridor", key=corridor)
    for refinery, grades in REFINERIES.items():
        g.add_node(f"refinery:{refinery}", label=refinery, kind="refinery")
        for grade in set(grades):
            g.add_node(f"grade:{grade}", label=grade, kind="grade")
            g.add_edge(f"grade:{grade}", f"refinery:{refinery}", kind="compatible_with")

    for src in proc.SOURCES:
        supplier = f"supplier:{src.origin}"
        grade = f"grade:{proc._grade_label(src)}"
        g.add_node(
            supplier, label=src.origin, kind="supplier", grade=proc._grade_label(src),
            spare_mbd=src.spare_mbd, transit_days=src.transit_days,
        )
        g.add_node(grade, label=proc._grade_label(src), kind="grade")
        g.add_edge(supplier, f"corridor:{src.corridor}", kind="ships_via")
        g.add_edge(supplier, grade, kind="produces")
        # corridor delivers to every refinery
        for refinery in REFINERIES:
            g.add_edge(f"corridor:{src.corridor}", f"refinery:{refinery}", kind="delivers_to")

    return g


def impact_of_disruption(g: nx.DiGraph, disrupted: set[str]) -> dict:
    """Traverse the graph to find what a set of disrupted corridors affects.

    A supplier is **cut off** when *every* corridor it ships via is disrupted.
    Grades at risk are those produced only by cut-off suppliers.

    Args:
        g: The knowledge graph.
        disrupted: Corridor keys that are disrupted (e.g. ``{"hormuz"}``).

    Returns:
        Dict with ``cut_off_suppliers``, ``at_risk_volume_mbd``,
        ``resilient_suppliers`` and ``at_risk_grades``.
    """
    cut_off, resilient = [], []
    at_risk_volume = 0.0
    for node, data in g.nodes(data=True):
        if data.get("kind") != "supplier":
            continue
        corridors = [
            g.nodes[t]["key"]
            for _, t, e in g.out_edges(node, data=True)
            if e["kind"] == "ships_via"
        ]
        if corridors and all(c in disrupted for c in corridors):
            cut_off.append(data["label"])
            at_risk_volume += float(data.get("spare_mbd", 0) or 0)
        else:
            resilient.append(data["label"])

    # Grades still reachable from at least one resilient supplier.
    safe_grades = set()
    for node, data in g.nodes(data=True):
        if data.get("kind") == "supplier" and data["label"] in resilient:
            for _, t, e in g.out_edges(node, data=True):
                if e["kind"] == "produces":
                    safe_grades.add(g.nodes[t]["label"])
    all_grades = {d["label"] for _, d in g.nodes(data=True) if d.get("kind") == "grade"}

    return {
        "cut_off_suppliers": sorted(cut_off),
        "resilient_suppliers": sorted(resilient),
        "at_risk_volume_mbd": round(at_risk_volume, 3),
        "at_risk_grades": sorted(all_grades - safe_grades),
    }


def graph_payload(disrupted: set[str] | None = None, corridor_risk: dict[str, float] | None = None) -> dict:
    """Serialize the graph (+ optional live risk and impact) for the API/UI.

    Args:
        disrupted: Optional set of disrupted corridors to compute impact for.
        corridor_risk: Optional live probability per corridor to annotate nodes.

    Returns:
        Dict with ``nodes``, ``edges``, ``stats`` and (if ``disrupted`` given)
        ``impact``.
    """
    g = build_graph()
    disrupted = disrupted or set()
    corridor_risk = corridor_risk or {}

    nodes = []
    for node, data in g.nodes(data=True):
        entry = {"id": node, "label": data["label"], "kind": data["kind"]}
        if data["kind"] == "corridor":
            entry["key"] = data["key"]
            entry["disrupted"] = data["key"] in disrupted
            entry["risk"] = corridor_risk.get(data["key"])
        if data["kind"] == "supplier":
            entry["grade"] = data.get("grade")
            entry["spare_mbd"] = data.get("spare_mbd")
        nodes.append(entry)

    edges = [{"source": u, "target": v, "kind": d["kind"]} for u, v, d in g.edges(data=True)]

    payload = {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "suppliers": sum(1 for _, d in g.nodes(data=True) if d["kind"] == "supplier"),
            "corridors": sum(1 for _, d in g.nodes(data=True) if d["kind"] == "corridor"),
            "grades": sum(1 for _, d in g.nodes(data=True) if d["kind"] == "grade"),
            "refineries": sum(1 for _, d in g.nodes(data=True) if d["kind"] == "refinery"),
            "edges": g.number_of_edges(),
        },
    }
    if disrupted:
        payload["impact"] = impact_of_disruption(g, disrupted)
    return payload


if __name__ == "__main__":
    pay = graph_payload(disrupted={"hormuz", "redsea"})
    print("graph:", pay["stats"])
    print("impact of Hormuz+Red Sea disruption:")
    imp = pay["impact"]
    print("  cut off:", imp["cut_off_suppliers"])
    print("  at-risk volume:", imp["at_risk_volume_mbd"], "mb/d")
    print("  resilient:", imp["resilient_suppliers"])
    print("  at-risk grades:", imp["at_risk_grades"])
