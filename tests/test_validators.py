import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable

def run(script, *args):
    return subprocess.run([PY, str(ROOT / "scripts" / script), *map(str, args)], cwd=ROOT, text=True, capture_output=True)

class ValidatorsTest(unittest.TestCase):
    def test_snapshot_and_plan(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); snap = td / "snapshot"; dag = td / "dag.json"
            self.assertEqual(run("create_snapshot.py", "--out", snap, "--input", ROOT / "examples/inputs/brief.txt").returncode, 0)
            plan = json.loads((ROOT / "examples/plan.example.json").read_text())
            plan_path = td / "plan.json"; plan_path.write_text(json.dumps(plan))
            # validator resolves snapshot next to plan; move it into the expected location
            expected = td / "snapshot"; snap.rename(expected)
            result = run("validate_plan.py", plan_path, "--dag", dag, "--check-snapshot")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(dag.read_text())["waves"], [["T1", "T2"]])

    def test_snapshot_is_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); snap = td / "snapshot"
            self.assertEqual(run("create_snapshot.py", "--out", snap, "--input", ROOT / "examples/inputs/brief.txt").returncode, 0)
            result = run("create_snapshot.py", "--out", snap, "--input", ROOT / "examples/inputs/brief.txt")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("REFUSE", result.stderr + result.stdout)

    def test_results_acceptance_checks_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); (td / "results").mkdir(); (td / "outputs").mkdir()
            plan = json.loads((ROOT / "examples/plan.example.json").read_text())
            p = td / "plan.json"; p.write_text(json.dumps(plan)); (td / "dag.json").write_text(json.dumps({"waves": [["T1", "T2"]]}))
            for tid in ("T1", "T2"):
                artifact = td / "outputs" / (tid + ".json"); artifact.write_text("{}")
                (td / "results" / (tid + ".json")).write_text(json.dumps({"task_id": tid, "status": "DONE", "summary": "ok", "evidence": [{"path": str(artifact)}], "artifacts": {"report": str(artifact)}, "checks": [{"name": "exists", "status": "PASS"}], "confidence": 1, "issues": []}))
            out = td / "integration.json"
            result = run("validate_results.py", p, td / "dag.json", td / "results", "--out", out)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(out.read_text())["status"], "PASS")

    def test_cycle_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); plan = json.loads((ROOT / "examples/plan.example.json").read_text())
            plan["tasks"][0]["depends_on"] = [{"id":"T2","type":"ORDER","reason":"cycle"}]
            plan["tasks"][1]["depends_on"] = [{"id":"T1","type":"ORDER","reason":"cycle"}]
            p = td / "plan.json"; p.write_text(json.dumps(plan))
            result = run("validate_plan.py", p, "--dag", td / "dag.json")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cycle", result.stderr + result.stdout)

if __name__ == "__main__": unittest.main()
