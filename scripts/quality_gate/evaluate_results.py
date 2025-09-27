#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .config_loader import TestSuiteError, load_test_suite


def _load_ids(raw: str) -> set[str]:
    if not raw:
        return set()
    try:
        values = json.loads(raw)
    except json.JSONDecodeError:
        print(f"::error::Invalid JSON payload: {raw}", file=sys.stderr)
        sys.exit(1)
    return set(values)


def _load_records(results_dir: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not results_dir.exists():
        return records
    for file_path in results_dir.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"::warning::Unable to parse {file_path}: {exc}", file=sys.stderr)
            continue
        test_id = data.get("id")
        if not test_id:
            print(
                f"::warning::Result file {file_path} missing 'id' field",
                file=sys.stderr,
            )
            continue
        records[test_id] = data
    return records


def _bool_output(value: bool) -> str:
    return "true" if value else "false"


def main() -> int:
    suite_path = Path("webapp.test-suite.yaml")
    try:
        suite = load_test_suite(suite_path)
    except TestSuiteError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    config = suite.config
    checks = config.get("checks", [])
    gates_mapping = config.get("gates_mapping", [])

    blocking_expected = _load_ids(os.environ.get("BLOCKING", "[]"))
    non_blocking_expected = _load_ids(os.environ.get("NON_BLOCKING", "[]"))

    threshold_raw = os.environ.get("QUALITY_GATE_NON_BLOCKING_THRESHOLD", "0.8")
    try:
        non_blocking_threshold = float(threshold_raw)
    except (TypeError, ValueError):
        print(
            "::warning::Invalid QUALITY_GATE_NON_BLOCKING_THRESHOLD; defaulting to 0.8",
            file=sys.stderr,
        )
        non_blocking_threshold = 0.8

    results_dir = Path(os.environ.get("RESULTS_DIR", "quality-results"))
    records = _load_records(results_dir)

    missing_ids = sorted((blocking_expected | non_blocking_expected) - set(records))
    blocking_failures = sorted(
        test_id
        for test_id in blocking_expected
        if records.get(test_id, {}).get("status") != "passed"
    )
    non_blocking_failures = sorted(
        test_id
        for test_id in non_blocking_expected
        if records.get(test_id, {}).get("status") != "passed"
    )

    non_blocking_total = len(non_blocking_expected)
    non_blocking_passed = non_blocking_total - len(non_blocking_failures)
    non_blocking_ratio = (
        non_blocking_passed / non_blocking_total if non_blocking_total else 1.0
    )
    non_blocking_ratio_met = non_blocking_ratio >= non_blocking_threshold

    # Index expected tests by group for gate evaluation
    expected_by_group: dict[str, list[dict[str, object]]] = {}
    for group in checks:
        group_name = str(group.get("group"))
        for item in group.get("items", []):
            test_id = item.get("id")
            if not test_id:
                continue
            expected_by_group.setdefault(group_name, []).append(
                {
                    "id": test_id,
                    "blocking": bool(item.get("blocking", False)),
                }
            )

    gate_configuration_errors: list[str] = []
    gates_report: list[dict[str, object]] = []

    for gate in gates_mapping:
        gate_name = gate.get("name")
        gate_group = str(gate.get("group"))
        gate_blocking = bool(gate.get("blocking", True))
        expected_tests = expected_by_group.get(gate_group, [])
        if not expected_tests:
            gate_configuration_errors.append(
                f"Gate '{gate_name}' references unknown or empty group '{gate_group}'"
            )
            gates_report.append(
                {
                    "name": gate_name,
                    "group": gate_group,
                    "blocking": gate_blocking,
                    "status": "invalid",
                    "details": "No checks mapped to this group",
                }
            )
            continue

        executed_tests = [
            records[test_info["id"]]
            for test_info in expected_tests
            if test_info["id"] in records
        ]
        missing_tests = [
            test_info["id"]
            for test_info in expected_tests
            if test_info["id"] not in records
        ]
        failed_tests = [
            record["id"]
            for record in executed_tests
            if record.get("status") != "passed"
        ]

        if gate_blocking:
            status = "passed"
            details: list[str] = []
            if missing_tests:
                status = "failed"
                details.append(f"missing: {', '.join(missing_tests)}")
            if failed_tests:
                status = "failed"
                details.append(f"failed: {', '.join(failed_tests)}")
            if not details:
                details.append("all blocking checks passed")
            gates_report.append(
                {
                    "name": gate_name,
                    "group": gate_group,
                    "blocking": True,
                    "status": status,
                    "details": "; ".join(details),
                }
            )
        else:
            total = len(expected_tests)
            passed_count = sum(
                1 for record in executed_tests if record.get("status") == "passed"
            )
            ratio = passed_count / total if total else 1.0
            status = "passed"
            details = [f"{passed_count}/{total} passed (ratio={ratio:.2f})"]
            if missing_tests:
                status = "warning"
                details.append(f"missing: {', '.join(missing_tests)}")
            if ratio < non_blocking_threshold:
                status = "warning"
                details.append(f"ratio below threshold {non_blocking_threshold:.2f}")
            gates_report.append(
                {
                    "name": gate_name,
                    "group": gate_group,
                    "blocking": False,
                    "status": status,
                    "details": "; ".join(details),
                }
            )

    outputs = {
        "missing": _bool_output(bool(missing_ids)),
        "missing_ids": json.dumps(missing_ids),
        "blocking_failed": _bool_output(bool(blocking_failures)),
        "blocking_failed_ids": json.dumps(blocking_failures),
        "non_blocking_failed": _bool_output(bool(non_blocking_failures)),
        "non_blocking_failed_ids": json.dumps(non_blocking_failures),
        "non_blocking_ratio": f"{non_blocking_ratio:.2f}",
        "non_blocking_ratio_met": _bool_output(non_blocking_ratio_met),
        "non_blocking_threshold": f"{non_blocking_threshold:.2f}",
        "gates_report": json.dumps(gates_report),
        "gate_configuration_errors": json.dumps(gate_configuration_errors),
    }

    for key, value in outputs.items():
        print(f"{key}={value}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
