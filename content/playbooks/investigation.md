# Playbook: Investigation

> Use this playbook when investigating bugs, errors, or technical questions.

## Before Starting

### Load Context Packs
- [ ] `governance` — Verify-don't-guess principle
- [ ] Relevant domain pack (agent-data, infrastructure, web-frontend, directus)
- [ ] `current-sprint` — Current context

### Define the Question
- [ ] What exactly is broken or unclear?
- [ ] When did it start? (Check recent commits/deploys)
- [ ] What is the expected behavior vs actual behavior?
- [ ] Who reported it and what evidence exists?

## Investigation Process

### Step 1: Gather Evidence (DO NOT GUESS)
- [ ] Read actual error messages/logs
- [ ] Read the actual source code involved
- [ ] Check git log for recent changes: `git log --oneline -20`
- [ ] Check environment: local vs cloud, which endpoint

```bash
# Common diagnostic commands
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/info | python3 -m json.tool
gcloud run services logs read agent-data-test --region=asia-southeast1 --limit=20
```

### Step 2: Reproduce
- [ ] Can you reproduce the issue locally?
- [ ] What are the exact steps to trigger it?
- [ ] Document the reproduction steps

### Step 3: Narrow Down
- [ ] Is it a data issue? (Check Firestore/Qdrant)
- [ ] Is it a code issue? (Read the function, trace the flow)
- [ ] Is it a config issue? (Check env vars, secrets)
- [ ] Is it a deployment issue? (Compare local vs cloud behavior)

### Step 4: Root Cause
- [ ] Identify the exact line/config causing the issue
- [ ] Understand WHY it happens (not just WHERE)
- [ ] Check if this is a known pattern or new issue

### Step 5: Fix Assessment
- [ ] Is the fix within scope of current ticket?
- [ ] Does the fix follow governance rules? (No new code, hybrid, etc.)
- [ ] What's the blast radius of the fix?
- [ ] Can we verify the fix without side effects?

## Documenting Findings

### Investigation Report Format
Write to: `docs/operations/research/WEB-XX-investigation.md`

```markdown
# [WEB-XX] Investigation: <Title>

## Question
What we set out to understand.

## Evidence
What we found (logs, code snippets, test results).

## Root Cause
The actual reason for the behavior.

## Recommendation
What to do about it.

## Verification
How we confirmed our findings.
```

### Upload to Agent Data
```bash
# Via MCP tool
upload_document(path="docs/operations/research/web-XX-investigation.md", content="...")
```

## Rules
- NEVER guess the cause — verify with actual code/data
- NEVER fix something you don't understand
- ALWAYS document findings even if issue was minor
- If issue is out of scope → REPORT with findings, don't fix
- Keep investigation focused — don't go down unrelated rabbit holes
