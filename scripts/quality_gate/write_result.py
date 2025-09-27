#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        if default == "":
            print(f"::error::Missing environment variable {name}", file=sys.stderr)
            sys.exit(1)
        return default
    return value


def main() -> int:
    record = {
        "id": _env("TEST_ID"),
        "description": os.environ.get("DESCRIPTION", ""),
        "blocking": os.environ.get("BLOCKING", "True") in {"True", "true", "1"},
        "tool": os.environ.get("TOOL", ""),
        "owner": os.environ.get("OWNER", ""),
        "group": os.environ.get("GROUP", ""),
        "evidence": os.environ.get("EVIDENCE", ""),
        "exit_code": int(os.environ.get("EXIT_CODE", "0")),
        "status": os.environ.get("STATUS", "unknown"),
    }

    output_dir = Path(os.environ.get("RESULTS_DIR", "quality-results"))
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{record['id']}.json"
    file_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
