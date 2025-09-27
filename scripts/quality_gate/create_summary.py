#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])
    policy = os.environ.get("POLICY", "")
    blocking = json.loads(os.environ.get("BLOCKING") or "[]")
    non_blocking = json.loads(os.environ.get("NON_BLOCKING") or "[]")
    ratio = os.environ.get("NON_BLOCKING_RATIO", "0.00")
    ratio_met = (os.environ.get("NON_BLOCKING_RATIO_MET") or "true").lower() == "true"
    threshold = os.environ.get("NON_BLOCKING_THRESHOLD", "0.80")
    gates_report = json.loads(os.environ.get("GATES_REPORT") or "[]")

    lines = [
        "# Quality Gate Summary",
        f"Policy: {policy}",
        f"Blocking tests count: {len(blocking)}",
        f"Non-blocking tests count: {len(non_blocking)}",
        f"Non-blocking pass ratio: {ratio} (threshold {threshold})",
        f"Non-blocking ratio met: {'yes' if ratio_met else 'no'}",
        "",
        "## Gate Statuses",
    ]

    if not gates_report:
        lines.append("- No gates defined in configuration.")
    else:
        for gate in gates_report:
            gate_name = gate.get("name", "unknown gate")
            gate_group = gate.get("group", "?")
            gate_type = "blocking" if gate.get("blocking") else "non-blocking"
            status = gate.get("status", "unknown")
            details = gate.get("details", "")
            lines.append(
                f"- {gate_name} (group {gate_group}, {gate_type}): {status} — {details}"
            )

    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
