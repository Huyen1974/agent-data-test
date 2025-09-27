#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from .config_loader import TestSuiteError, load_test_suite


def main() -> int:
    suite_path = Path("webapp.test-suite.yaml")
    try:
        suite = load_test_suite(suite_path)
    except TestSuiteError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    config = suite.config
    policy = config.get("policy", "")
    checks = config.get("checks", [])
    if not checks:
        print("::error::No 'checks' section defined in configuration", file=sys.stderr)
        return 1

    matrix_entries: list[dict[str, object]] = []
    blocking_ids: list[str] = []
    non_blocking_ids: list[str] = []

    raw_threshold = config.get("non_blocking_pass_threshold", 0.8)
    try:
        non_blocking_threshold = float(raw_threshold)
    except (TypeError, ValueError):
        print(
            "::warning::Invalid 'non_blocking_pass_threshold' value; defaulting to 0.8",
            file=sys.stderr,
        )
        non_blocking_threshold = 0.8

    for group in checks:
        group_name = group.get("group", "unknown")
        for item in group.get("items", []):
            test_id = item.get("id")
            if not test_id:
                print(
                    f"::error::A test in group '{group_name}' is missing an id",
                    file=sys.stderr,
                )
                return 1

            tool = item.get("tool")
            if not tool:
                print(
                    f"::error::Test '{test_id}' is missing required 'tool' attribute",
                    file=sys.stderr,
                )
                return 1

            blocking_flag = bool(item.get("blocking", False))
            if blocking_flag:
                blocking_ids.append(test_id)
            else:
                non_blocking_ids.append(test_id)

            matrix_entries.append(
                {
                    "test_id": test_id,
                    "description": item.get("description", ""),
                    "blocking": blocking_flag,
                    "tool": tool,
                    "owner": item.get("owner", ""),
                    "group": group_name,
                    "evidence": item.get("evidence", ""),
                }
            )

    if not matrix_entries:
        print(
            "::error::No test entries were discovered in configuration", file=sys.stderr
        )
        return 1

    outputs = {
        "matrix": json.dumps({"include": matrix_entries}),
        "blocking_tests": json.dumps(blocking_ids),
        "non_blocking_tests": json.dumps(non_blocking_ids),
        "policy": policy,
        "non_blocking_threshold": f"{non_blocking_threshold:.2f}",
    }

    for key, value in outputs.items():
        print(f"{key}={value}")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
