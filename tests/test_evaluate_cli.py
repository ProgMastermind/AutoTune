import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EvaluateCliTests(unittest.TestCase):
    def valid_manifest(self) -> dict:
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
            "budget": {"max_attempts": 20},
        }

    def run_evaluate(
        self, manifest_path: Path, scenario_path: Path, evidence_path: Path
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
                "evaluate",
                str(manifest_path),
                str(scenario_path),
                str(evidence_path),
            ],
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )

    def test_successful_fake_evaluation_writes_comparable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest_path = path / "campaign.json"
            scenario_path = path / "baseline.json"
            evidence_path = path / "evidence.json"
            manifest = self.valid_manifest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            scenario_path.write_text(
                json.dumps(
                    {
                        "attempt_id": "baseline-001",
                        "outcome": "completed",
                        "commands": ["benchmark_gptoss.py --concurrency 1"],
                        "environment": {"atom_revision": "abc123"},
                        "metrics": {"decode_tokens_per_second": 291.6},
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_evaluate(manifest_path, scenario_path, evidence_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"status": "completed"})
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["attempt_id"], "baseline-001")
            self.assertEqual(evidence["status"], "completed")
            self.assertEqual(evidence["metrics"], {"decode_tokens_per_second": 291.6})
            self.assertEqual(
                evidence["campaign_contract_sha256"],
                hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            )

    def test_retryable_failure_is_evidence_not_a_successful_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest_path = path / "campaign.json"
            scenario_path = path / "failure.json"
            evidence_path = path / "evidence.json"
            manifest_path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
            scenario_path.write_text(
                json.dumps(
                    {
                        "attempt_id": "candidate-002",
                        "outcome": "retryable_failure",
                        "failure": {"classification": "server_start_timeout"},
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_evaluate(manifest_path, scenario_path, evidence_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"status": "retryable_failure"})
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "retryable_failure")
            self.assertEqual(evidence["failure"], {"classification": "server_start_timeout"})
            self.assertNotIn("metrics", evidence)

    def test_completed_evaluation_requires_a_metric(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest_path = path / "campaign.json"
            scenario_path = path / "invalid.json"
            evidence_path = path / "evidence.json"
            manifest_path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
            scenario_path.write_text(
                json.dumps({"attempt_id": "candidate-003", "outcome": "completed"}),
                encoding="utf-8",
            )

            result = self.run_evaluate(manifest_path, scenario_path, evidence_path)

            self.assertEqual(result.returncode, 2)
            self.assertIn("scenario.metrics", result.stderr)
            self.assertFalse(evidence_path.exists())


if __name__ == "__main__":
    unittest.main()
