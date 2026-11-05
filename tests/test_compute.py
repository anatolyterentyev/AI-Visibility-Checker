"""Round-trip test: split the chiaro.ai run into probe batches, reassemble, recompute.

    python3 -m unittest discover tests
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compute as C  # noqa: E402

RAW = ROOT / "examples" / "chiaro.ai" / "run-12" / "report.raw.json"


def probe_outputs(raw: dict, size: int):
    """Turn a finished report back into the probe outputs that produced it."""
    plan = {"target": raw["target"], "use_case": raw.get("use_case", ""), "mindmap": raw["mindmap"]}
    by_prompt = {p["prompt"]: p for p in raw["prompts"]}
    outs = []
    for b in C.split(plan, size):
        for e in raw["engines"]:
            outs.append({"mode": "visibility", "engine": e["id"], "batch": b["batch"], "results": [
                {"prompt": p, "brands": [{"name": n} for n in by_prompt[p]["results"][e["id"]]["brands"]],
                 "citations": [], "answer_summary": by_prompt[p]["results"][e["id"]]["summary"],
                 **{k: by_prompt[p]["results"][e["id"]][k] for k in ("mentioned", "cited", "rank")}}
                for p in b["prompts"] if e["id"] in by_prompt[p]["results"]]})
    engines_with_scores = {eid for s in raw["sentiment"] for eid in s["by_engine"]}
    for eid in engines_with_scores:
        outs.append({"mode": "sentiment", "engine": eid, "scores": [
            {"brand": s["brand"], **s["by_engine"][eid]} for s in raw["sentiment"] if eid in s["by_engine"]]})
    return plan, outs


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(RAW.read_text())
        self.expected = C.compute(json.loads(RAW.read_text()))

    def test_chiaro_numbers(self):
        v = self.expected["visibility"]
        self.assertEqual(v["overall_pct"], 5.6)
        self.assertEqual(v["answers"], 36)
        self.assertEqual({k: x["pct"] for k, x in v["by_engine"].items()},
                         {"chatgpt": 0.0, "claude": 8.3, "gemini": 8.3})
        board = {b["brand"]: b["share_of_voice_pct"] for b in self.expected["leaderboard"]}
        self.assertEqual(board, {"Smartify": 31.0, "Google Arts & Culture": 19.0, "Bloomberg Connects": 19.0,
                                 "izi.TRAVEL": 17.2, "VoiceMap": 10.3, "Chiaro": 3.4})

    def test_split_sizes(self):
        plan, _ = probe_outputs(self.raw, 5)
        self.assertEqual([len(b["prompts"]) for b in C.split(plan, 5)], [5, 5, 2])

    def test_assemble_matches_any_batch_size(self):
        for size in (1, 5, 10, 50):
            plan, outs = probe_outputs(self.raw, size)
            got = C.compute(C.assemble(plan, [{k: e[k] for k in ("id", "label", "model")}
                                              for e in self.raw["engines"]], outs[::-1]))
            self.assertEqual(got["visibility"], self.expected["visibility"], size)
            strip = lambda board: [{k: v for k, v in b.items() if k != "domain"} for b in board]
            self.assertEqual(strip(got["leaderboard"]), strip(self.expected["leaderboard"]), size)
            self.assertEqual([s["index"] for s in got["sentiment"]],
                             [s["index"] for s in self.expected["sentiment"]], size)

    def test_missing_batch_marks_engine_partial(self):
        plan, outs = probe_outputs(self.raw, 5)
        outs = [o for o in outs if not (o["mode"] == "visibility" and o["engine"] == "gemini" and o["batch"] == "b1")]
        r = C.assemble(plan, [{"id": e["id"], "label": e["label"]} for e in self.raw["engines"]], outs)
        self.assertEqual({e["id"]: e["status"] for e in r["engines"]},
                         {"chatgpt": "ok", "claude": "ok", "gemini": "partial"})
        self.assertEqual(C.compute(r)["visibility"]["by_engine"]["gemini"]["answered"], 7)

    def test_fenced_probe_output_is_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.json"
            f.write_text('Here you go:\n```json\n{"mode": "sentiment", "engine": "x", "scores": []}\n```')
            self.assertEqual(C.load(f)["engine"], "x")
            f.write_text(json.dumps({"answer": '{"mode": "sentiment", "engine": "y", "scores": []}'}))
            self.assertEqual(C.load(f)["engine"], "y")

    def test_probe_fields_inferred_from_file_name(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "sent-gemini.json"
            f.write_text('{"scores": [{"brand": "X", "likelihood": 50}]}')
            o = C.load_probe(f)
            self.assertEqual((o["mode"], o["engine"]), ("sentiment", "gemini"))
            f = Path(d) / "vis-claude-b2.json"
            f.write_text('{"results": []}')
            o = C.load_probe(f)
            self.assertEqual((o["mode"], o["engine"], o["batch"]), ("visibility", "claude", "b2"))

    def test_cli_end_to_end(self):
        plan, outs = probe_outputs(self.raw, 10)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "plan.json").write_text(json.dumps(plan))
            (d / "engines.json").write_text(json.dumps(self.raw["engines"]))
            (d / "probes").mkdir()
            for i, o in enumerate(outs):
                (d / "probes" / f"{i}.json").write_text(json.dumps(o))
            run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts" / "compute.py"), *a],
                                            check=True, capture_output=True, text=True).stdout
            self.assertEqual(len(run("split", str(d / "plan.json")).splitlines()), 2)
            run("assemble", str(d / "plan.json"), str(d / "engines.json"), str(d / "probes"), str(d / "raw.json"))
            self.assertIn("Smartify", run("competitors", str(d / "raw.json")))
            self.assertIn("visibility 5.6%", run("compute", str(d / "raw.json"), str(d / "out")))
            self.assertTrue((d / "out" / "data.js").read_text().startswith("window.REPORT = {"))


class PublishSite(unittest.TestCase):
    """The FlyMyAI Lab route: full-mode probe answers -> publish_site.py -> site files."""

    def test_full_mode_run_matches_the_published_report(self):
        run = ROOT / "examples" / "chiaro.ai" / "run-30"
        plan = json.loads((run / "plan.json").read_text())
        engines = json.loads((run / "engines.json").read_text())
        expected = json.loads((run / "report.json").read_text())
        probes = []
        for e in engines:  # merge each engine's batches and sentiment into one full-mode answer
            full = {"mode": "full", "engine": e["id"], "results": [], "scores": []}
            for f in sorted((run / "probes").glob(f"*-{e['id']}*.json")):
                o = C.load_probe(f)
                full["results"] += [{k: r[k] for k in ("prompt", "brands", "mentioned", "cited", "rank")}
                                    for r in o.get("results", [])]
                full["scores"] += o.get("scores", [])
            probes.append(json.dumps(full) if e["id"] == "claude" else full)  # text or dict both work
        cfg = {"base_url": str(ROOT), "plan": plan, "engines": engines, "probes": probes}
        with tempfile.TemporaryDirectory() as d:
            out = subprocess.run(
                [sys.executable, "-c",
                 "import json,sys;CFG=json.load(sys.stdin);"
                 f"exec(compile(open({str(ROOT / 'scripts' / 'publish_site.py')!r}).read(),'p','exec'),"
                 "{'__name__':'__main__','CFG':CFG})"],
                input=json.dumps(cfg), capture_output=True, text=True, cwd=d, check=True).stdout
            line = next(l for l in out.splitlines() if l.startswith("<<<SITE>>>"))
            site = json.loads(line[len("<<<SITE>>>"):])
            data = (Path(d) / "site_out" / "data.js").read_text()
            self.assertTrue((Path(d) / "site_out" / "index.html").read_text().startswith("<!doctype html>"))
        self.assertEqual(site["visibility_pct"], expected["visibility"]["overall_pct"])
        self.assertEqual(site["by_engine"], {k: v["pct"] for k, v in expected["visibility"]["by_engine"].items()})
        self.assertEqual(site["leaderboard"], [[b["brand"], b["share_of_voice_pct"]] for b in expected["leaderboard"]])
        self.assertIn("1 of 90 AI answers", site["summary"][0])
        report = json.loads(data[len("window.REPORT = "):-2])
        self.assertNotIn("citations", report["prompts"][0]["results"]["chatgpt"])


if __name__ == "__main__":
    unittest.main()
