from __future__ import annotations

import hashlib
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


def _read_json(path: Path, subject: str) -> tuple[Any | None, int | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as error:
        print(f"Cannot read {subject}: {error}", file=sys.stderr)
        return None, 2
    except json.JSONDecodeError as error:
        print(f"Invalid JSON in {subject}: {error.msg}", file=sys.stderr)
        return None, 2


def _write_json(path: Path, value: Any) -> int:
    try:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"Cannot write dossier: {error}", file=sys.stderr)
        return 2
    return 0


def validate_command(path_value: str) -> int:
    manifest, read_error = _read_json(Path(path_value), "campaign manifest")
    if read_error is not None:
        return read_error

    errors = validate_campaign_contract(manifest)
    if errors:
        print("Campaign contract is invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print(json.dumps({"valid": True}))
    return 0


def initialize_dossier_command(manifest_path_value: str, dossier_path_value: str) -> int:
    manifest, read_error = _read_json(Path(manifest_path_value), "campaign manifest")
    if read_error is not None:
        return read_error

    errors = validate_campaign_contract(manifest)
    if errors:
        print("Campaign contract is invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    dossier = {
        "schema_version": 1,
        "campaign_id": manifest["campaign_id"],
        "model": {
            "id": manifest["model"]["id"],
            "architecture": manifest["model"]["architecture"],
        },
        "target": {
            "gpu_arch": manifest["target"]["gpu_arch"],
            "compute_units": manifest["target"]["compute_units"],
        },
        "facts": [],
        "compatibility": [],
        "techniques": [],
    }
    dossier_path = Path(dossier_path_value)
    write_error = _write_json(dossier_path, dossier)
    if write_error:
        return write_error
    print(json.dumps({"created": str(dossier_path)}))
    return 0


def validate_technique(technique: Any) -> list[str]:
    errors: list[str] = []
    record = _required_mapping(technique, "technique", errors)
    _required_string(record.get("id"), "technique.id", errors)
    _required_string(record.get("lane"), "technique.lane", errors)
    _required_string(record.get("provenance"), "technique.provenance", errors)
    preconditions = record.get("preconditions")
    if not isinstance(preconditions, list) or not preconditions:
        errors.append("technique.preconditions must be a non-empty list")
    elif any(not isinstance(precondition, str) or not precondition.strip() for precondition in preconditions):
        errors.append("technique.preconditions must contain non-empty strings")
    return errors


def add_technique_command(dossier_path_value: str, technique_path_value: str) -> int:
    dossier_path = Path(dossier_path_value)
    dossier, dossier_read_error = _read_json(dossier_path, "dossier")
    if dossier_read_error is not None:
        return dossier_read_error
    technique, technique_read_error = _read_json(Path(technique_path_value), "technique")
    if technique_read_error is not None:
        return technique_read_error

    dossier_errors = []
    dossier_record = _required_mapping(dossier, "dossier", dossier_errors)
    techniques = dossier_record.get("techniques")
    if not isinstance(techniques, list):
        dossier_errors.append("dossier.techniques must be a list")
    technique_errors = validate_technique(technique)
    errors = dossier_errors + technique_errors
    if errors:
        print("Technique cannot be added:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    if any(existing.get("id") == technique["id"] for existing in techniques if isinstance(existing, dict)):
        print(f"Technique cannot be added:\n- technique.id {technique['id']} already exists", file=sys.stderr)
        return 2
    techniques.append(technique)
    write_error = _write_json(dossier_path, dossier_record)
    if write_error:
        return write_error
    print(json.dumps({"added": technique["id"]}))
    return 0


def validate_scenario(scenario: Any) -> list[str]:
    errors: list[str] = []
    record = _required_mapping(scenario, "scenario", errors)
    _required_string(record.get("attempt_id"), "scenario.attempt_id", errors)
    outcome = record.get("outcome")
    allowed_outcomes = {"completed", "retryable_failure", "terminal_failure"}
    if outcome not in allowed_outcomes:
        errors.append(
            "scenario.outcome must be completed, retryable_failure, or terminal_failure"
        )
    if outcome == "completed":
        metrics = record.get("metrics")
        if not isinstance(metrics, dict) or not metrics:
            errors.append("scenario.metrics must be a non-empty object for completed outcomes")
    if outcome in {"retryable_failure", "terminal_failure"}:
        failure = _required_mapping(record.get("failure"), "scenario.failure", errors)
        _required_string(
            failure.get("classification"), "scenario.failure.classification", errors
        )
    commands = record.get("commands", [])
    if not isinstance(commands, list) or any(
        not isinstance(command, str) or not command.strip() for command in commands
    ):
        errors.append("scenario.commands must be a list of non-empty strings")
    environment = record.get("environment", {})
    if not isinstance(environment, dict):
        errors.append("scenario.environment must be an object")
    return errors


def evaluate_command(
    manifest_path_value: str, scenario_path_value: str, evidence_path_value: str
) -> int:
    manifest, manifest_read_error = _read_json(Path(manifest_path_value), "campaign manifest")
    if manifest_read_error is not None:
        return manifest_read_error
    contract_errors = validate_campaign_contract(manifest)
    if contract_errors:
        print("Campaign contract is invalid:", file=sys.stderr)
        for error in contract_errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    scenario, scenario_read_error = _read_json(Path(scenario_path_value), "scenario")
    if scenario_read_error is not None:
        return scenario_read_error
    scenario_errors = validate_scenario(scenario)
    if scenario_errors:
        print("Evaluation scenario is invalid:", file=sys.stderr)
        for error in scenario_errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    evidence = {
        "schema_version": 1,
        "campaign_id": manifest["campaign_id"],
        "campaign_contract_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "attempt_id": scenario["attempt_id"],
        "status": scenario["outcome"],
        "commands": scenario.get("commands", []),
        "environment": scenario.get("environment", {}),
    }
    if scenario["outcome"] == "completed":
        evidence["metrics"] = scenario["metrics"]
    else:
        evidence["failure"] = scenario["failure"]

    write_error = _write_json(Path(evidence_path_value), evidence)
    if write_error:
        return write_error
    print(json.dumps({"status": scenario["outcome"]}))
    return 0


def decide_command(
    manifest_path_value: str,
    dossier_path_value: str,
    history_path_value: str,
    decision_path_value: str,
) -> int:
    manifest, manifest_read_error = _read_json(Path(manifest_path_value), "campaign manifest")
    if manifest_read_error is not None:
        return manifest_read_error
    contract_errors = validate_campaign_contract(manifest)
    if contract_errors:
        print("Campaign contract is invalid:", file=sys.stderr)
        for error in contract_errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    dossier, dossier_read_error = _read_json(Path(dossier_path_value), "dossier")
    if dossier_read_error is not None:
        return dossier_read_error
    history, history_read_error = _read_json(Path(history_path_value), "history")
    if history_read_error is not None:
        return history_read_error

    errors: list[str] = []
    dossier_record = _required_mapping(dossier, "dossier", errors)
    history_record = _required_mapping(history, "history", errors)
    techniques = dossier_record.get("techniques")
    attempts = history_record.get("attempts")
    evaluated_ids = history_record.get("evaluated_technique_ids")
    if not isinstance(techniques, list):
        errors.append("dossier.techniques must be a list")
    if not isinstance(attempts, list):
        errors.append("history.attempts must be a list")
    if not isinstance(evaluated_ids, list) or any(
        not isinstance(identifier, str) for identifier in evaluated_ids or []
    ):
        errors.append("history.evaluated_technique_ids must be a list of strings")
    if errors:
        print("Decision inputs are invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    if len(attempts) >= manifest["budget"]["max_attempts"]:
        decision = {"action": "stop", "reason": "max_attempts_exhausted"}
    else:
        candidate = next(
            (
                technique
                for technique in techniques
                if isinstance(technique, dict)
                and not validate_technique(technique)
                and technique["id"] not in evaluated_ids
            ),
            None,
        )
        if candidate is None:
            decision = {"action": "stop", "reason": "no_unevaluated_technique"}
        else:
            decision = {
                "action": "evaluate",
                "candidate_id": candidate["id"],
                "lane": candidate["lane"],
                "max_additional_attempts": 1,
                "rationale": (
                    "Unevaluated Technique Catalog entry with documented preconditions "
                    "and provenance."
                ),
            }

    write_error = _write_json(Path(decision_path_value), decision)
    if write_error:
        return write_error
    print(json.dumps({"action": decision["action"]}))
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) == 3 and arguments[:2] == ["campaign", "validate"]:
        return validate_command(arguments[2])
    if len(arguments) == 5 and arguments[:3] == ["campaign", "dossier", "initialize"]:
        return initialize_dossier_command(arguments[3], arguments[4])
    if len(arguments) == 5 and arguments[:3] == ["campaign", "dossier", "add-technique"]:
        return add_technique_command(arguments[3], arguments[4])
    if len(arguments) == 5 and arguments[:2] == ["campaign", "evaluate"]:
        return evaluate_command(arguments[2], arguments[3], arguments[4])
    if len(arguments) == 6 and arguments[:2] == ["campaign", "decide"]:
        return decide_command(arguments[2], arguments[3], arguments[4], arguments[5])

    print(
        "Usage: python -m autotune campaign validate <manifest.json>\n"
        "       python -m autotune campaign dossier initialize <manifest.json> <dossier.json>\n"
        "       python -m autotune campaign dossier add-technique <dossier.json> <technique.json>\n"
        "       python -m autotune campaign evaluate <manifest.json> <scenario.json> <evidence.json>\n"
        "       python -m autotune campaign decide <manifest.json> <dossier.json> <history.json> <decision.json>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
