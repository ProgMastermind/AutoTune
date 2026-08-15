import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DossierCliTests(unittest.TestCase):
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

    def run_command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ | {
            "PYTHONPATH": str(Path(__file__).parents[1] / "src")
        }
        return subprocess.run(
            [sys.executable, "-m", "autotune", *arguments],
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )

    def test_initialize_creates_versioned_dossier_from_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "campaign.json"
            dossier_path = Path(directory) / "dossier.json"
            manifest_path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")

            result = self.run_command(
                "campaign", "dossier", "initialize", str(manifest_path), str(dossier_path)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"created": str(dossier_path)})
            self.assertEqual(
                json.loads(dossier_path.read_text(encoding="utf-8")),
                {
                    "schema_version": 1,
                    "campaign_id": "gpt-oss-120b-mi300x",
                    "model": {"id": "openai/gpt-oss-120b", "architecture": "gpt-oss"},
                    "target": {"gpu_arch": "gfx942", "compute_units": 304},
                    "facts": [],
                    "compatibility": [],
                    "techniques": [],
                },
            )

    def test_add_technique_requires_lane_preconditions_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "campaign.json"
            dossier_path = Path(directory) / "dossier.json"
            technique_path = Path(directory) / "technique.json"
            manifest_path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
            technique_path.write_text(
                json.dumps(
                    {
                        "id": "eagle3-num-spec-1",
                        "lane": "serving-strategy",
                        "preconditions": ["eagle3 is available"],
                        "provenance": "known gpt-oss-120b benchmark result",
                    }
                ),
                encoding="utf-8",
            )
            self.run_command(
                "campaign", "dossier", "initialize", str(manifest_path), str(dossier_path)
            )

            result = self.run_command(
                "campaign", "dossier", "add-technique", str(dossier_path), str(technique_path)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"added": "eagle3-num-spec-1"})
            dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
            self.assertEqual(dossier["techniques"], [json.loads(technique_path.read_text())])

    def test_add_technique_rejects_missing_preconditions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "campaign.json"
            dossier_path = Path(directory) / "dossier.json"
            technique_path = Path(directory) / "technique.json"
            manifest_path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
            technique_path.write_text(
                json.dumps(
                    {
                        "id": "unsafe-heuristic",
                        "lane": "kernel",
                        "provenance": "research note",
                    }
                ),
                encoding="utf-8",
            )
            self.run_command(
                "campaign", "dossier", "initialize", str(manifest_path), str(dossier_path)
            )

            result = self.run_command(
                "campaign", "dossier", "add-technique", str(dossier_path), str(technique_path)
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("technique.preconditions", result.stderr)


if __name__ == "__main__":
    unittest.main()
