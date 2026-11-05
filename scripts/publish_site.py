#!/usr/bin/env python3
"""AI Visibility Checker - build the report and publish it as a FlyMyAI site.

Runs INSIDE a FlyMyAI agent's sandbox (the FlyMyAI Lab route of PROMPT.md).
The publisher agent defines CFG and runs this file; it never writes the
report anywhere else: no chat files, no cloud-storage links.

CFG = {
  "repo":    "anatolyterentyev/AI-Visibility-Checker",   # where compute.py and the page live
  "branch":  "main",
  "plan":    {...},           # the planner's plan JSON (or its text)
  "engines": [{"id": "chatgpt", "label": "ChatGPT", "model": "gpt-6-sol"}, ...],
  "probes":  [{...}, ...],    # each probe's answer, as returned (dict or text)
  "budget_note": "...",       # optional line for the report's notes
}

It downloads scripts/compute.py and artifact/index.html from the repo,
recomputes every number, writes the insights from those numbers, publishes
index.html + data.js with the sites tool and prints one line:
<<<SITE>>>{"site_url": ..., "visibility_pct": ..., "summary": [...], "notes": [...]}

Outside FlyMyAI (no `flymy` module) it writes the two files to ./site_out/
instead, which is how the tests run it.
"""
import json
import re
import time
import types
import urllib.request

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"


def fetch(cfg, path):
    base = cfg.get("base_url")  # tests: a local folder
    if base:
        with open(f"{base.rstrip('/')}/{path}", encoding="utf-8") as f:
            return f.read()
    url = RAW.format(repo=cfg.get("repo", "anatolyterentyev/AI-Visibility-Checker"),
                     branch=cfg.get("branch", "main"), path=path)
    err = None
    for _ in range(3):
        try:
            return urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
        except Exception as e:  # network hiccup: retry
            err = e
            time.sleep(2)
    raise SystemExit(f"could not download {url}: {err!r}")


def as_obj(x):
    """A probe answer may arrive as a dict, as JSON text, as text with a ```json
    fence or prose around it, or wrapped as {"answer": "<json>"}."""
    if isinstance(x, (dict, list)):
        obj = x
    else:
        s = str(x)
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            obj = json.loads(s[s.find("{"):s.rfind("}") + 1])
    if isinstance(obj, dict) and set(obj) == {"answer"} and isinstance(obj["answer"], str):
        return as_obj(obj["answer"])
    return obj


def main(cfg):
    src = fetch(cfg, "scripts/compute.py")
    C = types.ModuleType("compute")
    exec(compile(src, "compute.py", "exec"), C.__dict__)
    page = fetch(cfg, "artifact/index.html")

    plan = as_obj(cfg["plan"])
    engines = cfg["engines"]
    probes = []
    for i, p in enumerate(cfg.get("probes") or []):
        o = as_obj(p)
        if "mode" not in o:
            o["mode"] = "full" if (("results" in o and "scores" in o) or "r" in o) else ("sentiment" if "scores" in o else "visibility")
        if not o.get("engine") and i < len(engines):
            o["engine"] = engines[i]["id"]  # probes are passed in engine order
        probes.append(o)

    report = C.assemble(plan, engines, probes)
    report = C.compute(report)
    report["insights"] = C.insights(report)
    scored = {C.norm(s["brand"]) for s in report.get("sentiment", [])}
    unscored = [b["brand"] for b in report["leaderboard"] if not b["is_target"] and C.norm(b["brand"]) not in scored]
    if unscored:
        report["notes"].append("Sentiment was scored for the competitors found when planning; "
                               f"{', '.join(unscored)} came up in the answers but were not scored.")
    if cfg.get("budget_note"):
        report["notes"].append(str(cfg["budget_note"]))

    # data.js feeds the page only: per-answer citations, domains and summaries stay out
    lean = json.loads(json.dumps(report))
    for p in lean.get("prompts", []):
        for res in p.get("results", {}).values():
            for k in ("citations", "domains", "summary"):
                res.pop(k, None)
    data_js = "window.REPORT = " + json.dumps(lean, ensure_ascii=False, separators=(",", ":")) + ";\n"

    name = f"AI Visibility - {report['target'].get('domain') or report['target'].get('name')} - {report['generated_at'][:10]}"
    files = [{"path": "index.html", "content": page},
             {"path": "data.js", "content": data_js},
             {"path": "flymy.site.json",
              "content": json.dumps({"schema": "flymyai.site.calls/v1", "calls": [], "permissions": []})}]

    try:
        import flymy  # present only inside a FlyMyAI sandbox
    except ImportError:
        flymy = None
    site_url = None
    if flymy is None:
        import os
        os.makedirs("site_out", exist_ok=True)
        for f in files:
            with open(os.path.join("site_out", f["path"]), "w", encoding="utf-8") as fh:
                fh.write(f["content"])
        site_url = "file://site_out/index.html"
    else:
        key = "aivc-site-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] + "-" + str(int(time.time()))
        out = flymy.tool("custom--sites--site_publish", {"name": name, "files": files}, operation_key=key)
        text = json.dumps(out)
        m = re.search(r'"owner_url":\s*"([^"]+)"', text) or re.search(r'"public_url":\s*"([^"]+)"', text)
        site_url = m.group(1) if m else None
        if not site_url:
            raise SystemExit("site_publish did not return a link: " + text[:500])

    v = report["visibility"]
    print("<<<SITE>>>" + json.dumps({
        "site_url": site_url,
        "visibility_pct": v["overall_pct"], "answers": v["answers"], "pts_per_answer": v["pts_per_answer"],
        "by_engine": {e: x["pct"] for e, x in v["by_engine"].items()},
        "leaderboard": [[b["brand"], b["share_of_voice_pct"]] for b in report["leaderboard"]],
        "sentiment": [[s["brand"], s["index"]] for s in sorted(report["sentiment"], key=lambda s: -s["index"])],
        "summary": report["insights"], "notes": report["notes"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main(CFG)  # noqa: F821 - CFG is defined by the code that runs this file
