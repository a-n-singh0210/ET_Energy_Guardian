"""rag.py — Retrieval-Augmented Generation over a geopolitical/commodity corpus.

Real vector RAG: a curated, cited intelligence corpus is embedded with Gemini
dense embeddings (``gemini-embedding-001``), a question is embedded and matched
by cosine similarity, and the top passages are handed to Gemini to generate a
grounded, cited answer. If no API key is present it falls back to TF-IDF vector
retrieval (scikit-learn) and returns the passages without generation — so it
still works offline.

Embeddings are cached to ``data/processed/rag_index.json`` so the corpus is only
embedded once.
"""

from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "data" / "processed" / "rag_index.json"
GEMINI_KEY_ENV = "GEMINI_API_KEY"
EMBED_MODEL = "gemini-embedding-001"
GEN_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Curated intelligence corpus. Every passage is factual and sourced; the model
# may only answer from these + is told to cite them.
CORPUS: list[dict[str, str]] = [
    {"id": "hormuz", "source": "EIA / problem statement",
     "text": "The Strait of Hormuz carries about 20 million barrels per day of oil and products, roughly 20% of global supply. It has almost no bypass: only ~2.6 mb/d of spare pipeline capacity (Saudi East-West and UAE Fujairah) can route around it. India sends 40-45% of its crude imports through Hormuz."},
    {"id": "redsea", "source": "EIA / ITF-OECD",
     "text": "The Bab-el-Mandeb strait and Suez Canal carry about 8-9 mb/d of oil and products. Unlike Hormuz, Red Sea traffic can reroute around the Cape of Good Hope, adding roughly 10-14 days of voyage time but avoiding the chokepoint, so its lasting price impact is smaller."},
    {"id": "india_imports", "source": "EIA 2024",
     "text": "India imports about 4.84 million barrels per day of crude, ~88% of its needs, making it the world's third-largest crude importer. Its 2024 supplier mix was Russia 36%, Iraq 21%, Saudi Arabia 13%, UAE 9%, United States 3.5%."},
    {"id": "spr", "source": "EIA / problem statement",
     "text": "India's Strategic Petroleum Reserve holds about 21.4 million barrels, roughly 9.5 days of cover at a full import halt. Including commercial and refinery stocks total cover is about 70-74 days. The SPR is decision-critical in the first days of a disruption."},
    {"id": "price_elasticity", "source": "energy economics",
     "text": "Oil demand is very price-inelastic in the short run (elasticity ~0.05-0.1), so a small supply loss produces a large price spike. A few percent of lost global supply can move Brent by tens of percent."},
    {"id": "gdp_sensitivity", "source": "empirical studies",
     "text": "For India, a sustained $10 rise in Brent cuts GDP growth by roughly 0.25-0.27 percentage points, widens the current-account deficit by ~0.4-0.5% of GDP, and adds ~30 bps to inflation."},
    {"id": "mckinsey", "source": "McKinsey (problem statement)",
     "text": "Economies without automated rerouting and demand-management capability took on average 47 days longer to stabilise supply after past energy shocks than those with integrated response intelligence."},
    {"id": "abqaiq", "source": "EIA / Reuters",
     "text": "The 2019 Abqaiq attack knocked out ~5.7 mb/d of Saudi output and sent Brent up about 15% in a single day, the largest single-event supply loss on record before it was largely restored within weeks."},
    {"id": "gulf_war", "source": "historical",
     "text": "The 1990 Gulf War removed ~4.3 mb/d of Iraqi and Kuwaiti supply and roughly doubled Brent, a benchmark for a severe Persian Gulf supply shock."},
    {"id": "russia_2022", "source": "historical",
     "text": "Russia's 2022 invasion of Ukraine pushed Brent to ~$130 (+30%) as ~3 mb/d of Russian flows were re-routed and sanctioned; India sharply increased discounted Russian Urals purchases in response."},
    {"id": "redsea_2023", "source": "Reuters / ITF-OECD",
     "text": "Houthi attacks on Red Sea shipping from late 2023 pushed container freight rates up ~130% and forced diversions around the Cape, though the crude price impact was modest because oil could reroute."},
    {"id": "grades", "source": "refining",
     "text": "Crude grades differ by API gravity and sulfur: light sweet (high API, low sulfur), medium, and heavy sour (low API, high sulfur). India's high-complexity refineries such as Jamnagar can process heavy sour grades, widening its sourcing options."},
    {"id": "alt_sources", "source": "trade flows",
     "text": "Non-Hormuz alternative crude for India includes West African (Nigeria, Angola), Atlantic-basin (US WTI, Brazil, Guyana) and Latin American (Venezuela, Mexico) grades, routed via the Cape of Good Hope, typically 22-42 days transit."},
    {"id": "hormuz_traffic", "source": "IMF PortWatch (AIS)",
     "text": "AIS data shows roughly 19,500 tanker transits through the Strait of Hormuz — about 60% of all its vessel traffic — underlining how oil-critical the chokepoint is relative to others."},
    {"id": "compound_thesis", "source": "EnergyGuardian",
     "text": "EnergyGuardian models compound risk: weak signals (price, freight, corridor events) interacting produce elevated systemic risk that independent per-signal monitoring misses. Co-elevation of heterogeneous signals is the key early-warning."},
    {"id": "opec_spare", "source": "energy markets",
     "text": "OPEC+ spare capacity, largely in Saudi Arabia and the UAE, can offset some supply loss — but most of it sits behind the Strait of Hormuz, so it cannot help if Hormuz itself is the disruption."},
]


def _gemini_embed(text: str, api_key: str, task: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
    """Embed one text with Gemini. Returns None on failure."""
    try:  # pragma: no cover - network
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent?key={api_key}"
        body = json.dumps({
            "content": {"parts": [{"text": text}]},
            "taskType": task,
        }).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return r["embedding"]["values"]
    except Exception:  # noqa: BLE001
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def build_index(api_key: str) -> dict | None:
    """Embed the whole corpus and cache it. Returns the index or None on failure."""
    vectors = []
    for doc in CORPUS:
        v = _gemini_embed(doc["text"], api_key, task="RETRIEVAL_DOCUMENT")
        if v is None:
            return None
        vectors.append(v)
    index = {"model": EMBED_MODEL, "ids": [d["id"] for d in CORPUS], "vectors": vectors}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index))
    return index


def _load_index() -> dict | None:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text())
        except Exception:  # noqa: BLE001
            return None
    return None


def _tfidf_retrieve(query: str, k: int) -> list[dict]:
    """Offline fallback: TF-IDF vector retrieval over the corpus."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [d["text"] for d in CORPUS]
    vec = TfidfVectorizer(stop_words="english")
    mat = vec.fit_transform(texts + [query])
    sims = cosine_similarity(mat[-1], mat[:-1])[0]
    order = sims.argsort()[::-1][:k]
    return [{**CORPUS[i], "score": round(float(sims[i]), 3)} for i in order]


def retrieve(query: str, k: int = 4) -> tuple[list[dict], str]:
    """Retrieve the top-k corpus passages for a query.

    Returns:
        ``(passages, method)`` where method is "gemini" (dense) or "tfidf".
    """
    api_key = os.environ.get(GEMINI_KEY_ENV)
    if api_key:
        index = _load_index() or build_index(api_key)
        if index:
            qv = _gemini_embed(query, api_key, task="RETRIEVAL_QUERY")
            if qv:
                scored = [
                    {**CORPUS[i], "score": round(_cosine(qv, index["vectors"][i]), 3)}
                    for i in range(len(CORPUS))
                ]
                scored.sort(key=lambda d: d["score"], reverse=True)
                return scored[:k], "gemini"
    return _tfidf_retrieve(query, k), "tfidf"


def _gemini_generate(query: str, passages: list[dict], api_key: str) -> str | None:
    """Generate a grounded answer from retrieved passages. None on failure."""
    try:  # pragma: no cover - network
        context = "\n".join(f"[{p['id']}] {p['text']} (source: {p['source']})" for p in passages)
        prompt = (
            "You are an energy-supply-chain analyst. Answer the question using ONLY "
            "the numbered context passages. Be concise (3-5 sentences). Cite passages "
            f"inline like [hormuz]. If the context is insufficient, say so.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEN_MODEL}:generateContent?key={api_key}"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                           "generationConfig": {"temperature": 0.2}}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return r["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:  # noqa: BLE001
        return None


def ask(query: str, k: int = 4) -> dict:
    """Full RAG: retrieve then (if possible) generate a grounded answer.

    Args:
        query: The user's question.
        k: Number of passages to retrieve.

    Returns:
        Dict with ``answer`` (or None), ``sources`` (retrieved passages),
        ``retrieval`` method and ``generated`` flag.
    """
    passages, method = retrieve(query, k=k)
    api_key = os.environ.get(GEMINI_KEY_ENV)
    answer = _gemini_generate(query, passages, api_key) if api_key else None
    return {
        "query": query,
        "answer": answer,
        "generated": answer is not None,
        "retrieval": method,
        "sources": [{"id": p["id"], "text": p["text"], "source": p["source"], "score": p.get("score")} for p in passages],
    }


SAMPLE_QUESTIONS = [
    "What happens to India if the Strait of Hormuz closes?",
    "Why does a small supply loss cause a big price spike?",
    "How does the Red Sea disruption differ from a Hormuz disruption?",
    "What are India's alternative crude sources and how long do they take?",
    "How long can India's strategic reserves last?",
]


if __name__ == "__main__":
    out = ask("What happens to India if the Strait of Hormuz closes?")
    print("retrieval:", out["retrieval"], "| generated:", out["generated"])
    print("\nANSWER:\n", out["answer"])
    print("\nSOURCES:")
    for s in out["sources"]:
        print(f"  [{s['id']}] score={s['score']} — {s['text'][:70]}...")
