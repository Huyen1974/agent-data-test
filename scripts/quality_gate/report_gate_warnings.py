#!/usr/bin/env python3
from __future__ import annotations

import json
import os


def main() -> int:
    gates_report = json.loads(os.environ.get("GATES_REPORT") or "[]")
    for gate in gates_report:
        if gate.get("status") == "warning":
            name = gate.get("name", "unknown gate")
            details = gate.get("details", "")
            print(f"::warning::Gate '{name}' reported warning: {details}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
