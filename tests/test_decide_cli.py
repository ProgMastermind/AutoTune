import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DecideCliTests(unittest.TestCase):
    def manifest(self, max_attempts: int = 3) -> dict:
        return {
            "campaign_id": "gpt-oss-120b-mi300x",
            "model": {"id": "openai/gpt-oss-120b", "architecture": "gpt-oss"},
            "target": {
                "accelerator": "AMD MI300X",
                "gpu_arch": "gfx942",
                "compute_units": 304,
                "serving_engine": "ATOM",
                "kernel_library": "aiter",
            },
            "evaluation": {
                "primary_profile": {
                    "benchmark_id": "decode-long-context",
                    "repeat_count": 5,
                }
            },
            "budget": {"max_attempts": max_attempts},
        }

    def dossier(self) -> dict:
        return {
            "schema_version": 1,
            "campaign_id": "gpt-oss-120b-mi300x",
            "model": {"id": "openai/gpt-oss-120b", "architecture": "gpt-oss"},
            "target": {"gpu_arch": "gfx942", "compute_units": 304},
            "facts": [],
            "compatibility": [],
            "techniques": [
                {
                    "id": "eagle3-num-spec-1",
                    "lane": "serving-strategy",
                    "preconditions": ["eagle3 is available"],
                    "provenance": "known benchmark result",
                }
            ],
        }

    def run_decide(
        self, manifest_path: Path, dossier_path: Path, history_path: Path, decision_path: Path
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ | {
            "PYTHONPATH": str(Path(__file__).parents[1] / "src")
        }
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "autotune",
                "campaign",
                "decide",
                str(manifest_path),
                str(dossier_path),
                str(history_path),
                str(decision_path),
            ],
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )

    def test_selects_one_unevaluated_candidate_with_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest_path = path / "campaign.json"
            dossier_path = path / "dossier.json"
            history_path = path / "history.json"
            decision_path = path / "decision.json"
            manifest_path.write_text(json.dumps(self.manifest()), encoding="utf-8")
            dossier_path.write_text(json.dumps(self.dossier()), encoding="utf-8")
            history_path.write_text(
                json.dumps({"attempts": [], "evaluated_technique_ids": []}), encoding="utf-8"
            )

            result = self.run_decide(manifest_path, dossier_path, history_path, decision_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"action": "evaluate"})
            self.assertEqual(
                json.loads(decision_path.read_text(encoding="utf-8")),
                {
                    "action": "evaluate",
                    "candidate_id": "eagle3-num-spec-1",
                    "lane": "serving-strategy",
                    "max_additional_attempts": 1,
                    "rationale": "Unevaluated Technique Catalog entry with documented preconditions and provenance.",
                },
            )

    def test_stops_when_the_attempt_budget_is_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest_path = path / "campaign.json"
            dossier_path = path / "dossier.json"
            history_path = path / "history.json"
            decision_path = path / "decision.json"
            manifest_path.write_text(json.dumps(self.manifest(max_attempts=1)), encoding="utf-8")
            dossier_path.write_text(json.dumps(self.dossier()), encoding="utf-8")
            history_path.write_text(
                json.dumps({"attempts": [{"status": "completed"}], "evaluated_technique_ids": []}),
                encoding="utf-8",
            )

            result = self.run_decide(manifest_path, dossier_path, history_path, decision_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"action": "stop"})
            self.assertEqual(
                json.loads(decision_path.read_text(encoding="utf-8")),
                {"action": "stop", "reason": "max_attempts_exhausted"},
            )

    def test_stops_when_every_technique_has_already_been_evaluated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest_path = path / "campaign.json"
            dossier_path = path / "dossier.json"
            history_path = path / "history.json"
            decision_path = path / "decision.json"
            manifest_path.write_text(json.dumps(self.manifest()), encoding="utf-8")
            dossier_path.write_text(json.dumps(self.dossier()), encoding="utf-8")
            history_path.write_text(
                json.dumps(
                    {"attempts": [], "evaluated_technique_ids": ["eagle3-num-spec-1"]}
                ),
                encoding="utf-8",
            )

            result = self.run_decide(manifest_path, dossier_path, history_path, decision_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(decision_path.read_text(encoding="utf-8")), {"action": "stop", "reason": "no_unevaluated_technique"})


if __name__ == "__main__":
    unittest.main()
