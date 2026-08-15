import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CampaignValidateCliTests(unittest.TestCase):
    def run_validate(self, manifest: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "campaign.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            environment = os.environ | {
                "PYTHONPATH": str(Path(__file__).parents[1] / "src")
            }
            return subprocess.run(
                [sys.executable, "-m", "autotune", "campaign", "validate", str(manifest_path)],
                capture_output=True,
                check=False,
                text=True,
                env=environment,
            )

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

    def test_valid_contract_returns_machine_readable_success(self) -> None:
        result = self.run_validate(self.valid_manifest())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"valid": True})

    def test_missing_budget_limit_returns_actionable_contract_error(self) -> None:
        manifest = self.valid_manifest()
        manifest["budget"] = {}

        result = self.run_validate(manifest)

        self.assertEqual(result.returncode, 2)
        self.assertIn("budget.max_attempts", result.stderr)


if __name__ == "__main__":
    unittest.main()
