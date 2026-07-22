"""news_agent.py — Geopolitical Risk Intelligence Agent (live).

Ingests live news headlines (Google News RSS — genuinely live, no key), extracts
structured disruption events from each headline, and aggregates them into a
**live disruption-probability score per corridor and per supplier**.

Extraction uses the free Google Gemini API (AI Studio) when an API key is
present; otherwise it falls back to a transparent keyword classifier so the
agent still runs offline. Every score is a documented, recomputable function of
the ingested headlines — no fabricated feeds.
"""

from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

# LLM extraction: Google Gemini (AI Studio free tier). Set GEMINI_API_KEY.
GEMINI_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# One search query per corridor / theme.
CORRIDOR_QUERIES: dict[str, str] = {
    "hormuz": "Strait of Hormuz OR Persian Gulf tanker OR Iran oil export",
    "redsea": "Red Sea shipping OR Houthi attack OR Bab-el-Mandeb OR Suez Canal",
    "global": "OPEC oil production OR crude oil sanctions OR oil supply disruption",
}

# Keyword → (severity 0-5) for the deterministic fallback classifier.
_SEVERITY_KEYWORDS: dict[str, int] = {
    "closure": 5, "blockade": 5, "embargo": 5, "shut": 5, "war": 5,
    "attack": 4, "strike": 4, "missile": 4, "seize": 4, "seized": 4,
    "drone": 4, "suspend": 4, "halt": 4, "divert": 4, "blast": 4,
    "sanction": 3, "sanctions": 3, "threat": 3, "warn": 2, "tension": 2,
    "risk": 2, "disrupt": 3, "escalat": 3,
}
# Checked in order; the most specific/unambiguous corridor terms come first so a
# "Red Sea … Iran" headline resolves to Red Sea rather than Hormuz.
_CORRIDOR_KEYWORDS: dict[str, list[str]] = {
    "redsea": ["red sea", "houthi", "bab-el-mandeb", "bab el mandeb", "suez", "yemen", "aden"],
    "hormuz": ["hormuz", "persian gulf", "gulf of oman", "iran", "iranian"],
    "global": ["opec", "sanction", "supply", "output", "production cut"],
}
_SUPPLIERS: dict[str, dict[str, object]] = {
    "Iran": {"kw": ["iran", "iranian"], "corridor": "hormuz"},
    "Iraq": {"kw": ["iraq", "basra"], "corridor": "hormuz"},
    "Saudi Arabia": {"kw": ["saudi", "aramco"], "corridor": "hormuz"},
    "UAE": {"kw": ["uae", "emirates", "fujairah", "abu dhabi"], "corridor": "hormuz"},
    "Russia": {"kw": ["russia", "russian", "urals"], "corridor": "redsea"},
    "United States": {"kw": ["u.s.", "united states", "american", "wti"], "corridor": "atlantic_cape"},
    "Nigeria": {"kw": ["nigeria", "bonny"], "corridor": "atlantic_cape"},
}


@dataclass
class Headline:
    """One ingested news headline."""

    title: str
    source: str
    published: str
    link: str


@dataclass
class ExtractedEvent:
    """A structured disruption event extracted from a headline."""

    title: str
    source: str
    corridor: str  # hormuz | redsea | global | none
    supplier: str  # supplier name or "none"
    event_type: str
    severity: int  # 0-5
    confidence: float  # 0-1
    method: str = "keyword"  # "gemini" | "keyword"
    extras: dict = field(default_factory=dict)


def fetch_headlines(query: str, limit: int = 20) -> list[Headline]:
    """Fetch live headlines for a query from Google News RSS.

    Args:
        query: Search query.
        limit: Max headlines to return.

    Returns:
        List of :class:`Headline` (empty on network failure).
    """
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        data = urllib.request.urlopen(req, timeout=15).read()
    except Exception:  # noqa: BLE001 - degrade gracefully if offline
        return []
    root = ET.fromstring(data)
    out: list[Headline] = []
    for item in root.findall(".//item")[:limit]:
        src = item.find("{*}source")
        out.append(
            Headline(
                title=item.findtext("title") or "",
                source=src.text if src is not None and src.text else "news",
                published=item.findtext("pubDate") or "",
                link=item.findtext("link") or "",
            )
        )
    return out


def _keyword_extract(h: Headline, corridor_hint: str) -> ExtractedEvent:
    """Deterministic fallback: classify a headline by keyword rules."""
    text = h.title.lower()
    severity = 0
    matched_type = "mention"
    for kw, sev in _SEVERITY_KEYWORDS.items():
        if kw in text and sev > severity:
            severity = sev
            matched_type = kw
    corridor = "none"
    for c, kws in _CORRIDOR_KEYWORDS.items():
        if any(k in text for k in kws):
            corridor = c
            break
    if corridor == "none":
        corridor = corridor_hint
    supplier = "none"
    for name, meta in _SUPPLIERS.items():
        if any(k in text for k in meta["kw"]):  # type: ignore[index]
            supplier = name
            break
    n_hits = sum(1 for kw in _SEVERITY_KEYWORDS if kw in text)
    confidence = min(0.9, 0.45 + 0.12 * n_hits) if severity > 0 else 0.2
    return ExtractedEvent(
        title=h.title, source=h.source, corridor=corridor, supplier=supplier,
        event_type=matched_type, severity=severity, confidence=round(confidence, 2),
        method="keyword",
    )


_EXTRACT_SYSTEM = (
    "You extract structured energy-supply-disruption signals from news "
    "headlines. For each headline return a JSON object with: corridor "
    "(one of hormuz, redsea, global, none), supplier (Iran, Iraq, Saudi "
    "Arabia, UAE, Russia, United States, Nigeria, or none), event_type "
    "(short phrase), severity (integer 0-5, 0=not a disruption), "
    "confidence (0-1). Return ONLY a JSON array, one object per headline, "
    "same order. Do not invent facts beyond the headline text."
)


def _parse_events(raw: str, headlines: list[Headline], method: str, corridor_hint: str) -> list[ExtractedEvent]:
    """Parse a model's JSON-array response into ExtractedEvents (order-aligned)."""
    start, end = raw.find("["), raw.rfind("]")
    parsed = json.loads(raw[start : end + 1])
    out: list[ExtractedEvent] = []
    for h, obj in zip(headlines, parsed):
        out.append(
            ExtractedEvent(
                title=h.title, source=h.source,
                corridor=str(obj.get("corridor", corridor_hint)),
                supplier=str(obj.get("supplier", "none")),
                event_type=str(obj.get("event_type", "signal")),
                severity=int(obj.get("severity", 0)),
                confidence=float(obj.get("confidence", 0.5)),
                method=method,
            )
        )
    return out


def _gemini_extract(headlines: list[Headline], corridor_hint: str, api_key: str) -> list[ExtractedEvent] | None:
    """Free LLM extraction via Google Gemini (AI Studio). None on failure."""
    try:  # pragma: no cover - network path
        titles = [h.title for h in headlines]
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={api_key}"
        )
        body = json.dumps({
            "system_instruction": {"parts": [{"text": _EXTRACT_SYSTEM}]},
            "contents": [{"parts": [{"text": json.dumps(titles)}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        raw = resp["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_events(raw, headlines, "gemini", corridor_hint)
    except Exception:  # noqa: BLE001
        return None


def _corridor_probability(events: list[ExtractedEvent], corridor: str) -> float:
    """Aggregate matched disruption events into a 0-1 probability for a corridor.

    prob = 1 - exp(-0.4 · Σ (severity/5 · confidence)). Transparent and saturating.
    """
    raw = sum(
        (e.severity / 5.0) * e.confidence
        for e in events
        if e.corridor == corridor and e.severity > 0
    )
    return round(1.0 - math.exp(-0.4 * raw), 3)


def run_intel(per_query_limit: int = 15) -> dict[str, object]:
    """Run the full agent: ingest → extract → score.

    Args:
        per_query_limit: Headlines to pull per corridor query.

    Returns:
        Dict with headlines, extracted events, per-corridor and per-supplier
        probabilities, the extraction method used, and a UTC timestamp.
    """
    gemini_key = os.environ.get(GEMINI_KEY_ENV)
    all_events: list[ExtractedEvent] = []
    all_headlines: list[dict[str, str]] = []

    for corridor, query in CORRIDOR_QUERIES.items():
        heads = fetch_headlines(query, limit=per_query_limit)
        all_headlines += [
            {"title": h.title, "source": h.source, "published": h.published, "corridor_query": corridor}
            for h in heads
        ]
        events: list[ExtractedEvent] | None = None
        if gemini_key:  # free LLM extraction
            events = _gemini_extract(heads, corridor, gemini_key)
        if events is None:
            events = [_keyword_extract(h, corridor) for h in heads]
        all_events += events

    method = all_events[0].method if all_events else "keyword"

    corridor_scores = {c: _corridor_probability(all_events, c) for c in ("hormuz", "redsea", "global")}

    # Per-supplier probability: its corridor risk, nudged by direct mentions.
    supplier_scores: dict[str, float] = {}
    for name, meta in _SUPPLIERS.items():
        corridor = str(meta["corridor"])
        base = corridor_scores.get(corridor, 0.0)
        mentions = sum(1 for e in all_events if e.supplier == name and e.severity > 0)
        supplier_scores[name] = round(min(1.0, base * (1.0 + 0.08 * mentions)), 3)

    disruptions = [e for e in all_events if e.severity >= 3]
    disruptions.sort(key=lambda e: (e.severity, e.confidence), reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": method,
        "headline_count": len(all_headlines),
        "corridor_scores": corridor_scores,
        "supplier_scores": supplier_scores,
        "top_events": [
            {
                "title": e.title, "source": e.source, "corridor": e.corridor,
                "supplier": e.supplier, "event_type": e.event_type,
                "severity": e.severity, "confidence": e.confidence, "method": e.method,
            }
            for e in disruptions[:12]
        ],
    }


# --------------------------------------------------------------------------
# Single-article extraction (paste-an-article demo).
# A judge pastes a full news article; the LLM extracts one structured signal
# and we map it onto the scenario knobs so the compound/impact model can run.
# --------------------------------------------------------------------------

_EXTRACT_ONE_SYSTEM = (
    "You extract ONE structured energy-supply-disruption signal from a news "
    "article. Return a single JSON object with: corridor (one of hormuz, "
    "redsea, global, none), supplier (Iran, Iraq, Saudi Arabia, UAE, Russia, "
    "United States, Nigeria, or none), event_type (short phrase), severity "
    "(integer 0-5, 0=not a disruption, 5=corridor closure/war), confidence "
    "(0-1, how clearly the article supports this), and rationale (one short "
    "sentence grounded in the article). Return ONLY the JSON object. Do not "
    "invent facts beyond the article text."
)


def suggested_knobs(corridor: str, severity: int, confidence: float) -> tuple[dict[str, float], float]:
    """Map an extracted signal onto scenario knobs (transparent, documented).

    intensity = (severity / 5) · confidence, in [0, 1]. The article's corridor
    knob is set to that intensity; the others stay at a low baseline.
    """
    intensity = round((max(0, min(5, severity)) / 5.0) * max(0.0, min(1.0, confidence)), 3)
    knobs = {"h": 0.1, "r": 0.1, "o": 0.0}
    if corridor == "hormuz":
        knobs["h"] = max(knobs["h"], intensity)
    elif corridor == "redsea":
        knobs["r"] = max(knobs["r"], intensity)
    elif corridor == "global":
        knobs["o"] = intensity
    return knobs, intensity


def _gemini_extract_one(text: str, api_key: str) -> dict | None:
    """Extract one signal from article text via Gemini. None on failure."""
    try:  # pragma: no cover - network path
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={api_key}"
        )
        body = json.dumps({
            "system_instruction": {"parts": [{"text": _EXTRACT_ONE_SYSTEM}]},
            "contents": [{"parts": [{"text": text[:12000]}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        raw = resp["candidates"][0]["content"]["parts"][0]["text"]
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start : end + 1])
    except Exception:  # noqa: BLE001
        return None


def _keyword_extract_text(text: str) -> dict:
    """Deterministic offline fallback over arbitrary article text."""
    fake = Headline(title=text[:2000], source="pasted", published="", link="")
    ev = _keyword_extract(fake, "none")
    return {
        "corridor": ev.corridor, "supplier": ev.supplier, "event_type": ev.event_type,
        "severity": ev.severity, "confidence": ev.confidence,
        "rationale": "Matched deterministic keyword rules (offline fallback — set GEMINI_API_KEY for LLM).",
    }


def extract_article(text: str) -> dict:
    """Paste-an-article entry point: text → one structured signal → knobs.

    Prefers Gemini (free); falls back to a transparent keyword classifier so
    the demo always works offline. Never fabricates: on empty input it says so.
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "Paste an article first."}

    gemini_key = os.environ.get(GEMINI_KEY_ENV)
    result = _gemini_extract_one(text, gemini_key) if gemini_key else None
    method = "gemini"
    if result is None:
        result = _keyword_extract_text(text)
        method = "keyword"

    corridor = str(result.get("corridor", "none"))
    severity = int(result.get("severity", 0))
    confidence = float(result.get("confidence", 0.5))
    knobs, intensity = suggested_knobs(corridor, severity, confidence)
    return {
        "ok": True,
        "method": method,
        "corridor": corridor,
        "supplier": str(result.get("supplier", "none")),
        "event_type": str(result.get("event_type", "signal")),
        "severity": severity,
        "confidence": round(confidence, 2),
        "rationale": str(result.get("rationale", "")),
        "intensity": intensity,
        "suggested_knobs": knobs,
    }


if __name__ == "__main__":
    intel = run_intel()
    print(f"method={intel['method']} | headlines={intel['headline_count']} | "
          f"generated {intel['generated_at']}")
    print("corridor scores:", intel["corridor_scores"])
    print("supplier scores:", intel["supplier_scores"])
    print("\ntop disruption signals:")
    for e in intel["top_events"][:6]:
        print(f"  [{e['corridor']:6} sev{e['severity']} {e['confidence']:.2f}] {e['title'][:80]}")
