import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PromoteCliTests(unittest.TestCase):
    def run_promote(
        self, incumbent_path: Path, candidate_path: Path, promotion_path: Path
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
                "promote",
                str(incumbent_path),
                str(candidate_path),
                str(promotion_path),
            ],
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )

    def evidence(self, attempt_id: str, throughput: float, correctness: bool = True) -> dict:
        return {
            "attempt_id": attempt_id,
            "status": "completed",
            "metrics": {"decode_tokens_per_second": throughput},
            "correctness": {"passed": correctness},
        }

    def test_promotes_a_correct_candidate_that_improves_decode_throughput(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            incumbent_path = path / "incumbent.json"
            candidate_path = path / "candidate.json"
            promotion_path = path / "promotion.json"
            incumbent_path.write_text(json.dumps(self.evidence("baseline-001", 291.6)), encoding="utf-8")
            candidate_path.write_text(json.dumps(self.evidence("candidate-002", 300.1)), encoding="utf-8")

            result = self.run_promote(incumbent_path, candidate_path, promotion_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"action": "promote"})
            self.assertEqual(
                json.loads(promotion_path.read_text(encoding="utf-8")),
                {
                    "action": "promote",
                    "incumbent_attempt_id": "candidate-002",
                    "reason": "decode_tokens_per_second improved from 291.6 to 300.1",
                },
            )

    def test_retains_incumbent_when_candidate_fails_correctness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            incumbent_path = path / "incumbent.json"
            candidate_path = path / "candidate.json"
            promotion_path = path / "promotion.json"
            incumbent_path.write_text(json.dumps(self.evidence("baseline-001", 291.6)), encoding="utf-8")
            candidate_path.write_text(
                json.dumps(self.evidence("candidate-002", 300.1, correctness=False)),
                encoding="utf-8",
            )

            result = self.run_promote(incumbent_path, candidate_path, promotion_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"action": "retain"})
            self.assertEqual(
                json.loads(promotion_path.read_text(encoding="utf-8")),
                {"action": "retain", "reason": "candidate_correctness_failed"},
            )

    def test_retains_incumbent_when_throughput_does_not_improve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            incumbent_path = path / "incumbent.json"
            candidate_path = path / "candidate.json"
            promotion_path = path / "promotion.json"
            incumbent_path.write_text(json.dumps(self.evidence("baseline-001", 291.6)), encoding="utf-8")
            candidate_path.write_text(json.dumps(self.evidence("candidate-002", 291.6)), encoding="utf-8")

            result = self.run_promote(incumbent_path, candidate_path, promotion_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(promotion_path.read_text(encoding="utf-8")), {"action": "retain", "reason": "decode_throughput_not_improved"})


if __name__ == "__main__":
    unittest.main()
