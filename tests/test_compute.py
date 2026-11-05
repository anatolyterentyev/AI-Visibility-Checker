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

RAW = ROOT / "examples" / "chiaro.ai" / "report.raw.json"


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


if __name__ == "__main__":
    unittest.main()
