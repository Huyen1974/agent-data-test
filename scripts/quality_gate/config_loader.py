from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class TestSuite:
    config: dict
    sanitized_source: str


class TestSuiteError(RuntimeError):
    """Raised when the quality gate test suite cannot be loaded."""


def _sanitize_scalars(source: str) -> str:
    sanitized_lines = []
    for raw_line in source.splitlines():
        if ":" not in raw_line:
            sanitized_lines.append(raw_line)
            continue

        head, tail = raw_line.split(":", 1)
        value = tail.lstrip()
        if not value:
            sanitized_lines.append(raw_line)
            continue

        if value[0] in {'"', "'", "|", ">"}:
            sanitized_lines.append(raw_line)
            continue

        comment = ""
        value_body = value
        if "#" in value:
            value_body, comment = value.split("#", 1)
            comment = "#" + comment

        stripped_value = value_body.rstrip()
        if ":" not in stripped_value:
            sanitized_lines.append(raw_line)
            continue

        spacing = tail[: len(tail) - len(value)]
        escaped = stripped_value.replace('"', '\\"')
        rebuilt = f'{head}:{spacing}"{escaped}"'
        if comment:
            if not comment.startswith(" "):
                rebuilt += " "
            rebuilt += comment
        sanitized_lines.append(rebuilt)

    if not sanitized_lines:
        return source if source.endswith("\n") else source + "\n"

    sanitized = "\n".join(sanitized_lines)
    if source.endswith("\n"):
        sanitized += "\n"
    return sanitized


def load_test_suite(path: str | Path) -> TestSuite:
    suite_path = Path(path)
    if not suite_path.exists():
        raise TestSuiteError(f"Missing configuration file at {suite_path}")

    raw_text = suite_path.read_text(encoding="utf-8")
    sanitized_text = _sanitize_scalars(raw_text)

    try:
        config = yaml.safe_load(sanitized_text) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive logging
        problem_mark = getattr(exc, "problem_mark", None)
        context_lines: tuple[str, ...] = ()
        if problem_mark is not None:
            line_no = problem_mark.line + 1
            lines = sanitized_text.splitlines()
            start = max(line_no - 3, 1)
            end = min(line_no + 3, len(lines))
            context_lines = tuple(
                f"{idx}: {lines[idx - 1]}" for idx in range(start, end + 1)
            )
        details = [f"Unable to parse YAML file {suite_path}: {exc}"]
        if context_lines:
            details.append("Context:\n" + "\n".join(context_lines))
        raise TestSuiteError("\n".join(details)) from exc

    return TestSuite(config=config, sanitized_source=sanitized_text)


__all__ = ["TestSuite", "TestSuiteError", "load_test_suite"]
