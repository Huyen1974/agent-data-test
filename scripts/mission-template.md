# Mission Template — Agent Operating Procedure

> **EVERY mission MUST follow this template. No exceptions.**

---

## Step 0: Assembly (MANDATORY)

Before ANY code or action:

1. **Read Operating Rules**: `search_knowledge("operating rules SSOT")`
2. **Checkpoint**: Quote the "Mu 1:" line from Section IV to confirm you read it
3. **Read Merge Procedures**: `search_knowledge("merge procedures")`
4. **Search existing solutions**: `search_knowledge("<topic>")` — Assembly First (Section II)

If Step 0 is skipped, the mission is INVALID.

---

## Step 1: Plan

- Describe what you will do
- List files to modify
- Identify risks

---

## Step 2: Execute (Branch Workflow)

```bash
git checkout -b feat/<ticket-id>-<description>
# ... make changes ...
git add <specific-files>
git commit -m "feat: <description> (<ticket-id>)"
git push -u origin feat/<ticket-id>-<description>
gh pr create --title "feat: <description> (<ticket-id>)" --body "..."
```

**NEVER push directly to main.** Pre-push hook will block you.

---

## Step 3: CI GREEN

- Wait for CI to pass
- If CI fails: fix on the same branch, push again
- `gh pr merge <PR> --squash --delete-branch` only after CI GREEN

---

## Step 4: Verify on Production

- Check VPS health: `curl https://vps.incomexsaigoncorp.vn/api/health`
- Verify the specific change works on production
- **Merge + CI GREEN != done. Unverified = unfinished.**

---

## Step 5: Report

- Summary of changes
- Test results
- Production verification result
