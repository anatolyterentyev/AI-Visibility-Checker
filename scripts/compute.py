#!/usr/bin/env python3
"""Recompute every metric of an AI Visibility Checker report from its raw data.

The lead agent already computes the numbers, but LLM arithmetic can drift.
This script re-derives visibility, share of voice and sentiment index from
`prompts` and `sentiment`, so the published report is exactly reproducible.

    python3 scripts/compute.py examples/chiaro.ai/report.raw.json examples/chiaro.ai

writes <out>/report.json and <out>/data.js (load data.js next to
artifact/index.html). Standard library only.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path


def norm(name: str) -> str:
    """Canonical key for a brand name: 'izi.TRAVEL' == 'Izi Travel'."""
    n = name.lower()
    n = re.sub(r"\b(app|ai)\b", "", n)
    return re.sub(r"[^a-z0-9]", "", n)


def rnd(x: float) -> float:
    return round(x + 1e-9, 1)


def compute(r: dict) -> dict:
    engines = [e for e in r["engines"] if e.get("status", "ok") != "failed"]
    eids = [e["id"] for e in engines]
    target = r["target"]["name"]
    tkey = norm(target)

    # --- visibility ---------------------------------------------------------
    by_engine, ranks, pairs, hits, ment, cites = {}, [], 0, 0, 0, 0
    for eid in eids:
        answered = m = c = h = 0
        for p in r["prompts"]:
            res = p.get("results", {}).get(eid)
            if not res:
                continue
            answered += 1
            names = [norm(b) for b in res.get("brands", [])]
            mentioned = bool(res.get("mentioned")) or tkey in names
            cited = bool(res.get("cited"))
            if mentioned and res.get("rank") is None and tkey in names:
                res["rank"] = names.index(tkey) + 1
            res["mentioned"] = mentioned
            m += mentioned
            c += cited
            h += mentioned or cited
            if mentioned and res.get("rank"):
                ranks.append(res["rank"])
        by_engine[eid] = {"pct": rnd(100 * h / answered) if answered else 0.0,
                          "mentioned": m, "cited": c, "answered": answered}
        pairs += answered
        hits += h
        ment += m
        cites += c
    r["visibility"] = {
        "overall_pct": rnd(100 * hits / pairs) if pairs else 0.0,
        "mentions_pct": rnd(100 * ment / pairs) if pairs else 0.0,
        "citations_pct": rnd(100 * cites / pairs) if pairs else 0.0,
        "avg_rank": rnd(sum(ranks) / len(ranks)) if ranks else None,
        "by_engine": by_engine,
    }

    # --- share of voice -----------------------------------------------------
    counts, display = Counter(), {}
    for p in r["prompts"]:
        for eid in eids:
            res = p.get("results", {}).get(eid)
            if not res:
                continue
            for b in dict.fromkeys(norm(x) for x in res.get("brands", [])):
                counts[b] += 1
            for x in res.get("brands", []):
                display.setdefault(norm(x), x)
    old = {norm(b["brand"]): b for b in r.get("leaderboard", [])}
    sent = {norm(s["brand"]): s for s in r.get("sentiment", [])}
    # ties are broken in favour of brands that already have sentiment scores
    ranked = sorted((k for k in counts if k != tkey), key=lambda k: (-counts[k], k not in sent))
    competitors = ranked[:5]
    keys = [tkey] + competitors
    total = sum(counts[k] for k in keys) or 1

    # --- sentiment ----------------------------------------------------------
    for s in r.get("sentiment", []):
        scores = [v["likelihood"] for v in s.get("by_engine", {}).values()
                  if isinstance(v.get("likelihood"), (int, float))]
        s["index"] = round(sum(scores) / len(scores)) if scores else 0
        tones = Counter(v.get("tone") for v in s.get("by_engine", {}).values() if v.get("tone"))
        s["tone"] = tones.most_common(1)[0][0] if tones else "unknown"
        s["is_target"] = norm(s["brand"]) == tkey

    board = []
    for k in keys:
        prev = old.get(k, {})
        board.append({
            "brand": target if k == tkey else prev.get("brand", display.get(k, k)),
            "domain": r["target"]["domain"] if k == tkey else prev.get("domain", ""),
            "is_target": k == tkey,
            "mentions": counts[k],
            "share_of_voice_pct": rnd(100 * counts[k] / total),
            "mention_rate_pct": rnd(100 * counts[k] / pairs) if pairs else 0.0,
            "sentiment_index": sent[k]["index"] if k in sent else None,
        })
    r["leaderboard"] = sorted(board, key=lambda b: -b["share_of_voice_pct"])
    return r


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    report = compute(json.loads(Path(sys.argv[1]).read_text()))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    (out / "report.json").write_text(text + "\n")
    compact = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    (out / "data.js").write_text("window.REPORT = " + compact + ";\n")
    v = report["visibility"]
    print(f"visibility {v['overall_pct']}%  by engine " +
          ", ".join(f"{k} {x['pct']}%" for k, x in v["by_engine"].items()))
    for b in report["leaderboard"]:
        print(f"  {b['brand']:<24} SoV {b['share_of_voice_pct']:>5}%  mentions {b['mentions']:>2}  "
              f"sentiment {b['sentiment_index']}")


if __name__ == "__main__":
    main()
