#!/usr/bin/env python3
"""AI Visibility Checker — deterministic helpers (standard library only).

The agents do the asking; this script does the bookkeeping, so every number
in a report can be reproduced from the raw probe answers.

  split        plan.json [--size 10]
               Print the visibility batches (one JSON object per line):
               {"batch": "b1", "prompts": [...]} — send each batch to every
               engine's probe agent.

  assemble     plan.json engines.json probes_dir/ report.raw.json [--insights insights.json]
               Merge the plan and every probe output in probes_dir/ (*.json,
               visibility batches and sentiment answers, any order) into one
               raw report. Name files vis-<engine>-<batch>.json and
               sent-<engine>.json so engine and batch are known even when a
               model leaves them out of its JSON.

  competitors  report.raw.json [--top 5]
               Print the brands the engines recommended most (the brands to
               send to the sentiment probes, after the target).

  compute      report.raw.json out_dir/ [--auto-insights]
               Recompute every metric and write out_dir/report.json and
               out_dir/data.js (load data.js next to artifact/index.html).
               --auto-insights (or a report without insights) writes the
               insights from the computed numbers.
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------- helpers

def norm(name: str) -> str:
    """Canonical key for a brand name: 'izi.TRAVEL' == 'Izi Travel'."""
    n = name.lower()
    n = re.sub(r"\b(app|ai)\b", "", n)
    return re.sub(r"[^a-z0-9]", "", n)


def rnd(x: float) -> float:
    return round(x + 1e-9, 1)


def load(path) -> dict:
    """Read a JSON file; tolerate a ```json fence or prose around the object."""
    text = Path(path).read_text()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        obj = json.loads(text[start:end + 1])
    # some runs wrap the agent's JSON as {"answer": "<json string>"}
    if isinstance(obj, dict) and set(obj) == {"answer"} and isinstance(obj["answer"], str):
        inner = obj["answer"]
        obj = json.loads(inner[inner.find("{"):inner.rfind("}") + 1])
    return obj


def load_probe(path) -> dict:
    """Load a probe output, filling in fields a model sometimes leaves out:
    mode (from the content) and engine / batch (from a file name like
    vis-claude-b2.json or sent-gemini.json)."""
    obj = load(path)
    if "mode" not in obj:
        if "scores" in obj and "results" in obj:
            obj["mode"] = "full"
        else:
            obj["mode"] = "sentiment" if "scores" in obj else "visibility"
    m = re.match(r"(?:vis|sent|full)-([a-z0-9]+)(?:-(b\d+))?\.json$", Path(path).name)
    if m:
        obj.setdefault("engine", m.group(1))
        if m.group(2):
            obj.setdefault("batch", m.group(2))
    return obj


def brand_name(b) -> str:
    return b.get("name", "") if isinstance(b, dict) else str(b)


def flat_prompts(plan: dict):
    for br in plan["mindmap"]["branches"]:
        for p in br["prompts"]:
            yield br["intent"], p


def answers(r: dict, eids):
    for p in r["prompts"]:
        for eid in eids:
            res = p.get("results", {}).get(eid)
            if res is not None:
                yield p, eid, res


def live_engines(r: dict):
    return [e["id"] for e in r["engines"] if e.get("status", "ok") != "failed"]


# --------------------------------------------------------------------------- split

def split(plan: dict, size: int = 10):
    prompts = [p for _, p in flat_prompts(plan)]
    return [{"batch": f"b{i // size + 1}", "prompts": prompts[i:i + size]}
            for i in range(0, len(prompts), size)]


# --------------------------------------------------------------------------- assemble

def assemble(plan: dict, engines: list, probe_outputs: list, insights=None) -> dict:
    target = plan["target"]
    tkey = norm(target["name"])
    prompts = [{"prompt": p, "intent": intent, "results": {}} for intent, p in flat_prompts(plan)]
    index = {p["prompt"].strip().lower(): p for p in prompts}
    sentiment, seen_batches, notes = {}, {}, []

    for out in probe_outputs:
        eid = out.get("engine")
        mode = out.get("mode")
        if mode in ("visibility", "full"):
            seen_batches.setdefault(eid, set()).add(out.get("batch"))
            for res in out.get("results", []):
                p = index.get(str(res.get("prompt", "")).strip().lower())
                if p is None:
                    notes.append(f"{eid}: answer for unknown prompt ignored: {res.get('prompt')!r}")
                    continue
                names = [brand_name(b) for b in res.get("brands", [])]
                keys = [norm(n) for n in names]
                mentioned = bool(res.get("mentioned")) or tkey in keys
                rank = res.get("rank")
                if mentioned and rank is None and tkey in keys:
                    rank = keys.index(tkey) + 1
                p["results"][eid] = {
                    "mentioned": mentioned, "cited": bool(res.get("cited")), "rank": rank,
                    "brands": names, "citations": res.get("citations", []),
                    "summary": res.get("answer_summary", res.get("summary", "")),
                    "domains": {brand_name(b): b.get("domain") for b in res.get("brands", [])
                                if isinstance(b, dict) and b.get("domain")},
                }
        if mode in ("sentiment", "full"):
            for s in out.get("scores", []):
                entry = sentiment.setdefault(norm(s["brand"]), {"brand": s["brand"], "by_engine": {}})
                entry["by_engine"][eid] = {k: s.get(k) for k in
                                           ("likelihood", "tone", "description", "pros", "cons")}

    # Some engines (Gemini's Google Search grounding) return opaque redirect
    # links instead of source URLs, so a citation of the target can't be seen.
    redirect_hosts = ("vertexaisearch.cloud.google.com",)
    for e in engines:
        cites = [c for p in prompts for c in p["results"].get(e["id"], {}).get("citations", [])]
        hidden = sum(any(h in c for h in redirect_hosts) for c in cites)
        if cites and hidden / len(cites) > 0.2:
            notes.append(f"{hidden} of {len(cites)} {e['label']} citations are search-redirect links, "
                         f"not source URLs, so a citation of {target['domain']} could be missed there; "
                         f"mentions are unaffected.")

    total = len(prompts)
    eng = []
    for e in engines:
        got = sum(1 for p in prompts if e["id"] in p["results"])
        status = "ok" if got == total else ("partial" if got else "failed")
        if status != "ok":
            notes.append(f"{e['label']}: answers for {got} of {total} prompts.")
        eng.append({**e, "status": status})

    r = {
        "schema": "ai-visibility-checker.v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": target, "use_case": plan.get("use_case", ""), "mindmap": plan["mindmap"],
        "engines": eng, "prompts": prompts,
        "sentiment": list(sentiment.values()),
        "insights": insights or [], "notes": notes,
    }
    return r


# --------------------------------------------------------------------------- competitors

def brand_counts(r: dict):
    eids = live_engines(r)
    counts, spelling, domains = Counter(), {}, {}
    for _, _, res in answers(r, eids):
        names = res.get("brands", [])
        for k in dict.fromkeys(norm(n) for n in names):
            counts[k] += 1
        for n in names:
            spelling.setdefault(norm(n), Counter())[n] += 1
        for n, d in (res.get("domains") or {}).items():
            domains.setdefault(norm(n), d)
    display = {k: c.most_common(1)[0][0] for k, c in spelling.items()}
    return counts, display, domains


def competitors(r: dict, top: int = 5):
    tkey = norm(r["target"]["name"])
    counts, display, domains = brand_counts(r)
    scored = {norm(s["brand"]) for s in r.get("sentiment", [])}
    ranked = sorted((k for k in counts if k != tkey and k),
                    key=lambda k: (-counts[k], k not in scored, k))
    return [{"brand": display[k], "domain": domains.get(k, ""), "mentions": counts[k]}
            for k in ranked[:top]]


# --------------------------------------------------------------------------- compute

def compute(r: dict) -> dict:
    eids = live_engines(r)
    target = r["target"]["name"]
    tkey = norm(target)

    # visibility
    by_engine = {e: {"pct": 0.0, "mentioned": 0, "cited": 0, "answered": 0} for e in eids}
    ranks, total, hits, ment, cites = [], 0, 0, 0, 0
    for _, eid, res in answers(r, eids):
        keys = [norm(n) for n in res.get("brands", [])]
        res["mentioned"] = bool(res.get("mentioned")) or tkey in keys
        if res["mentioned"] and res.get("rank") is None and tkey in keys:
            res["rank"] = keys.index(tkey) + 1
        hit = res["mentioned"] or bool(res.get("cited"))
        b = by_engine[eid]
        b["answered"] += 1
        b["mentioned"] += res["mentioned"]
        b["cited"] += bool(res.get("cited"))
        b["hits"] = b.get("hits", 0) + hit
        total += 1
        hits += hit
        ment += res["mentioned"]
        cites += bool(res.get("cited"))
        if res["mentioned"] and res.get("rank"):
            ranks.append(res["rank"])
    for b in by_engine.values():
        b["pct"] = rnd(100 * b.pop("hits", 0) / b["answered"]) if b["answered"] else 0.0
    pct = lambda n: rnd(100 * n / total) if total else 0.0
    r["visibility"] = {
        "overall_pct": pct(hits), "mentions_pct": pct(ment), "citations_pct": pct(cites),
        "avg_rank": rnd(sum(ranks) / len(ranks)) if ranks else None,
        "answers": total, "hits": hits, "pts_per_answer": rnd(100 / total) if total else None,
        "by_engine": by_engine,
    }

    # per intent
    by_intent = []
    for br in r["mindmap"]["branches"]:
        rows = [p for p in r["prompts"] if p["intent"] == br["intent"]]
        n = h = 0
        leaders = Counter()
        for p in rows:
            for eid in eids:
                res = p["results"].get(eid)
                if res is None:
                    continue
                n += 1
                h += res["mentioned"] or bool(res.get("cited"))
                for k in dict.fromkeys(norm(x) for x in res.get("brands", [])):
                    leaders[k] += 1
        leaders.pop(tkey, None)
        _, display, _ = brand_counts(r)
        by_intent.append({"intent": br["intent"], "prompts": len(rows), "answers": n,
                          "pct": rnd(100 * h / n) if n else 0.0,
                          "leader": display.get(leaders.most_common(1)[0][0], "") if leaders else ""})
    r["by_intent"] = by_intent

    # sentiment
    for s in r.get("sentiment", []):
        scores = [v["likelihood"] for v in s.get("by_engine", {}).values()
                  if isinstance(v.get("likelihood"), (int, float))]
        s["index"] = round(sum(scores) / len(scores)) if scores else 0
        tones = Counter(v.get("tone") for v in s.get("by_engine", {}).values() if v.get("tone"))
        s["tone"] = tones.most_common(1)[0][0] if tones else "unknown"
        s["is_target"] = norm(s["brand"]) == tkey
    sent = {norm(s["brand"]): s for s in r.get("sentiment", [])}

    # leaderboard: target + top 5 competitors
    counts, display, domains = brand_counts(r)
    old = {norm(b["brand"]): b for b in r.get("leaderboard", [])}
    comps = [norm(c["brand"]) for c in competitors(r)]
    keys = [tkey] + comps
    denom = sum(counts[k] for k in keys) or 1
    board = []
    for k in keys:
        board.append({
            "brand": target if k == tkey else display.get(k, old.get(k, {}).get("brand", k)),
            "domain": r["target"]["domain"] if k == tkey else (domains.get(k) or old.get(k, {}).get("domain", "")),
            "is_target": k == tkey,
            "mentions": counts[k],
            "share_of_voice_pct": rnd(100 * counts[k] / denom),
            "mention_rate_pct": pct(counts[k]),
            "sentiment_index": sent[k]["index"] if k in sent else None,
        })
    r["leaderboard"] = sorted(board, key=lambda b: -b["share_of_voice_pct"])
    return r


# --------------------------------------------------------------------------- insights

def insights(r: dict) -> list:
    """Takeaways written from the computed numbers only, so no count can drift."""
    t = r["target"]["name"]
    v = r["visibility"]
    labels = {e["id"]: e["label"] for e in r["engines"]}
    out = [f"{t} was named or cited in {v.get('hits', 0)} of {v['answers']} AI answers "
           f"({v['overall_pct']}% visibility; one answer moves it by {v['pts_per_answer']} points)."]

    by_engine = v["by_engine"]
    zero = [labels.get(e, e) for e, x in by_engine.items() if x["answered"] and x["pct"] == 0]
    seen = sorted(((x["pct"], e) for e, x in by_engine.items() if x["pct"] > 0), reverse=True)
    if zero and seen:
        best = seen[0][1]
        how = "only " + labels.get(best, best) + " did" if len(seen) == 1 else labels.get(best, best) + " did most often"
        out.append(f"{' and '.join(zero)} never named {t}; {how} "
                   f"({by_engine[best]['pct']}%, {by_engine[best]['mentioned']} of {by_engine[best]['answered']} answers).")
    elif zero:
        out.append(f"None of the engines ({', '.join(zero)}) named {t} for any prompt.")

    intents = r.get("by_intent", [])
    absent = [b for b in intents if b["pct"] == 0]
    present = sorted((b for b in intents if b["pct"] > 0), key=lambda b: -b["pct"])
    if present:
        b = present[0]
        out.append(f"{t} shows up most for '{b['intent']}' ({b['pct']}%)"
                   + (f"; it is absent from {len(absent)} of {len(intents)} intents." if absent else "."))
    for b in absent[:2]:
        if b.get("leader"):
            out.append(f"For '{b['intent']}' AI recommends {b['leader']} most, and never {t}.")

    board = r.get("leaderboard", [])
    rivals = [b for b in board if not b["is_target"]]
    me = next((b for b in board if b["is_target"]), None)
    if rivals and me:
        top = rivals[0]
        out.append(f"{top['brand']} leads share of voice with {top['share_of_voice_pct']}% "
                   f"({top['mentions']} answers) against {t}'s {me['share_of_voice_pct']}%.")

    sent = {s["brand"]: s for s in r.get("sentiment", [])}
    mine = next((s for s in r.get("sentiment", []) if s.get("is_target")), None)
    others = sorted((s for s in r.get("sentiment", []) if not s.get("is_target")), key=lambda s: -s["index"])
    if mine:
        line = f"Sentiment index: {t} {mine['index']}/100"
        if others:
            line += f" vs. {others[0]['brand']} {others[0]['index']}/100 (the highest of the competitors)"
        lows = [labels.get(e, e) for e, x in mine["by_engine"].items()
                if isinstance(x.get("likelihood"), (int, float)) and (x["likelihood"] < 20 or x.get("tone") == "unknown")]
        highs = [labels.get(e, e) for e, x in mine["by_engine"].items()
                 if isinstance(x.get("likelihood"), (int, float)) and x["likelihood"] >= 70]
        if lows:
            line += f"; {' and '.join(lows)} barely know{'s' if len(lows) == 1 else ''} {t}"
        out.append(line + ".")
        if v["overall_pct"] < 10 and highs:
            one = len(highs) == 1
            out.append(f"Discovery, not reputation, is the gap: {' and '.join(highs)} rate{'s' if one else ''} {t} "
                       f"highly when asked about it, but rarely bring{'s' if one else ''} it up for buyer questions.")
        elif mine["index"] < 40:
            out.append(f"Reputation is a gap too: engines rate {t} low for this use case, so a clear, consistent "
                       f"product description across the web is the first fix.")
    return out


# --------------------------------------------------------------------------- cli

def write_outputs(report: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    # data.js feeds the page only: leave out per-answer citations, domains
    # and summaries it never shows (report.json keeps everything)
    lean = json.loads(json.dumps(report))
    for p in lean.get("prompts", []):
        for res in p.get("results", {}).values():
            res.pop("citations", None)
            res.pop("domains", None)
            res.pop("summary", None)
    compact = json.dumps(lean, ensure_ascii=False, separators=(",", ":"))
    (out / "data.js").write_text("window.REPORT = " + compact + ";\n")


def summary(report: dict) -> None:
    v = report["visibility"]
    print(f"visibility {v['overall_pct']}% over {v['answers']} answers "
          f"(1 answer = {v['pts_per_answer']} pts) | " +
          ", ".join(f"{k} {x['pct']}%" for k, x in v["by_engine"].items()))
    for b in report["leaderboard"]:
        print(f"  {b['brand']:<24} SoV {b['share_of_voice_pct']:>5}%  mentions {b['mentions']:>3}  "
              f"sentiment {b['sentiment_index']}")


def main(argv) -> None:
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, args = argv[1], argv[2:]
    opt = lambda name, default=None: args[args.index(name) + 1] if name in args else default
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]

    if cmd == "split":
        for b in split(load(pos[0]), int(opt("--size", 10))):
            print(json.dumps(b, ensure_ascii=False))
    elif cmd == "assemble":
        plan, engines = load(pos[0]), load(pos[1])
        engines = engines.get("engines", engines) if isinstance(engines, dict) else engines
        outputs = [load_probe(f) for f in sorted(Path(pos[2]).glob("*.json"))]
        given = load(opt("--insights")) if opt("--insights") else None
        if isinstance(given, dict):
            given = given.get("insights", [])
        report = assemble(plan, engines, outputs, given)
        Path(pos[3]).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"assembled {len(report['prompts'])} prompts, "
              f"{sum(len(p['results']) for p in report['prompts'])} answers, "
              f"{len(report['sentiment'])} brands with sentiment -> {pos[3]}")
        for n in report["notes"]:
            print("  note:", n)
    elif cmd == "competitors":
        print(json.dumps(competitors(load(pos[0]), int(opt("--top", 5))), indent=2, ensure_ascii=False))
    elif cmd == "compute":
        report = compute(load(pos[0]))
        if "--auto-insights" in args or not report.get("insights"):
            report["insights"] = insights(report)
        write_outputs(report, Path(pos[1]))
        summary(report)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
