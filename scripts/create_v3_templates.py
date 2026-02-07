"""
Create 3 document templates in the v3 knowledge base.
"""

import sys
import httpx

BASE_URL = "http://localhost:8000"
API_KEY = "test-key-local"

TEMPLATES = [
    {
        "path": "docs/templates/session-report.md",
        "parent_id": "docs/templates",
        "title": "Session Report Template",
        "content": """# [WEB-XX] Session Report

## Status: IN PROGRESS | COMPLETED | BLOCKED
**Date**: YYYY-MM-DD
**Branch**: feature/xxx

---

## Objective
What was the goal of this session?

## Changes Made

| File | Action | Description |
|------|--------|-------------|
| `path/to/file` | Modified | What changed |

## Test Results

```
Test 1: description  ✅ PASS / ❌ FAIL
Test 2: description  ✅ PASS / ❌ FAIL
```

## Issues Encountered
- Issue 1: description → Resolution
- Issue 2: description → Resolution

## Next Steps
- [ ] Task 1
- [ ] Task 2

## Notes
Any additional context or observations.
""",
    },
    {
        "path": "docs/templates/decision-record.md",
        "parent_id": "docs/templates",
        "title": "Decision Record Template (ADR)",
        "content": """# ADR-XXX: [Decision Title]

## Status: PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED
**Date**: YYYY-MM-DD
**Deciders**: [who made this decision]

---

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Options Considered

### Option A: [Name]
- **Pros**: ...
- **Cons**: ...

### Option B: [Name]
- **Pros**: ...
- **Cons**: ...

## Consequences

### Positive
- Benefit 1
- Benefit 2

### Negative
- Trade-off 1
- Trade-off 2

## References
- Link to related documents or issues
""",
    },
    {
        "path": "docs/templates/context-pack.md",
        "parent_id": "docs/templates",
        "title": "Context Pack Template",
        "content": """# Context Pack: [Topic Name]

## Purpose
What does this context pack prepare an AI agent to do?

## Prerequisites
- Required knowledge or access
- Related context packs to load first

## Architecture Overview
Brief system architecture relevant to this context.

## Key Files

| File | Purpose |
|------|---------|
| `path/to/file` | Description |

## Current State
What is the current status of this area?

## Conventions & Rules
- Convention 1
- Convention 2

## Common Tasks

### Task 1: [Name]
Step-by-step instructions.

### Task 2: [Name]
Step-by-step instructions.

## Known Issues & Gotchas
- Gotcha 1: explanation
- Gotcha 2: explanation

## Related Documents
- [Document 1](path)
- [Document 2](path)
""",
    },
]


def main():
    created = 0
    failed = 0

    with httpx.Client(timeout=30.0) as client:
        for tmpl in TEMPLATES:
            body = {
                "document_id": tmpl["path"],
                "parent_id": tmpl["parent_id"],
                "content": {"mime_type": "text/markdown", "body": tmpl["content"]},
                "metadata": {"title": tmpl["title"], "tags": ["template", "v3-structure"]},
            }
            try:
                resp = client.post(
                    f"{BASE_URL}/documents",
                    json=body,
                    headers={"X-API-Key": API_KEY},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    print(f"  PASS  {tmpl['path']} (rev {data.get('revision', '?')})")
                    created += 1
                else:
                    print(f"  FAIL  {tmpl['path']} -> HTTP {resp.status_code}: {resp.text[:200]}")
                    failed += 1
            except Exception as e:
                print(f"  FAIL  {tmpl['path']} -> {e}")
                failed += 1

    print(f"\nDone: {created} created, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
