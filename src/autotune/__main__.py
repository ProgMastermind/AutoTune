from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


def _required_string(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def _required_mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def _required_positive_integer(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        errors.append(f"{path} must be a positive integer")


def validate_campaign_contract(manifest: Any) -> list[str]:
    """Return externally useful contract errors, or an empty list when valid."""
    errors: list[str] = []
    root = _required_mapping(manifest, "campaign", errors)

    _required_string(root.get("campaign_id"), "campaign_id", errors)

    model = _required_mapping(root.get("model"), "model", errors)
    _required_string(model.get("id"), "model.id", errors)
    _required_string(model.get("architecture"), "model.architecture", errors)

    target = _required_mapping(root.get("target"), "target", errors)
    _required_string(target.get("accelerator"), "target.accelerator", errors)
    _required_string(target.get("gpu_arch"), "target.gpu_arch", errors)
    _required_positive_integer(target.get("compute_units"), "target.compute_units", errors)
    _required_string(target.get("serving_engine"), "target.serving_engine", errors)
    _required_string(target.get("kernel_library"), "target.kernel_library", errors)

    evaluation = _required_mapping(root.get("evaluation"), "evaluation", errors)
    primary_profile = _required_mapping(
        evaluation.get("primary_profile"), "evaluation.primary_profile", errors
    )
    _required_string(
        primary_profile.get("benchmark_id"),
        "evaluation.primary_profile.benchmark_id",
        errors,
    )
    _required_positive_integer(
        primary_profile.get("repeat_count"),
        "evaluation.primary_profile.repeat_count",
        errors,
    )

    budget = _required_mapping(root.get("budget"), "budget", errors)
    _required_positive_integer(budget.get("max_attempts"), "budget.max_attempts", errors)
    return errors


def validate_command(path_value: str) -> int:
    path = Path(path_value)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"Cannot read campaign manifest: {error}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(f"Invalid JSON in campaign manifest: {error.msg}", file=sys.stderr)
        return 2

    errors = validate_campaign_contract(manifest)
    if errors:
        print("Campaign contract is invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print(json.dumps({"valid": True}))
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) == 3 and arguments[:2] == ["campaign", "validate"]:
        return validate_command(arguments[2])

    print("Usage: python -m autotune campaign validate <manifest.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
