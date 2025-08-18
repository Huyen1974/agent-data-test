# UBLA Merge PR Script

This script (`scripts/merge_ubla_pr.sh`) automates the process of merging a PR after conducting a UBLA (Uniform Bucket Level Access) audit through a terraform plan workflow.

## Overview

The script follows the MERGE-UBLA-PR-v1 protocol to:

1. **Identify current branch and PR**
2. **Find or trigger terraform-apply-gated workflow**
3. **Wait for workflow completion and verify success**
4. **Download and audit terraform plan for UBLA changes**
5. **Create evidence files and commit them**
6. **Comment on PR and enable auto-merge**

## Prerequisites

### Required Tools
- `git` - for repository operations
- `jq` - for JSON parsing
- `gh` (GitHub CLI) - for GitHub API operations

### Authentication
```bash
gh auth login
```

### Repository Requirements
- Must have `.github/workflows/terraform-apply-gated.yml` workflow
- Workflow must produce `tfplan-text/tfplan.txt` artifact
- Must be run from a branch with an open PR

## Usage

### Basic Usage
```bash
cd /path/to/agent-data-test
bash scripts/merge_ubla_pr.sh
```

### Test Script
```bash
# Validate script without execution
bash scripts/test_merge_ubla_pr.sh
```

## What the Script Does

### Step A: Branch & PR Detection
- Identifies current git branch
- Finds associated PR number

### Step B: Workflow Management
- Looks for existing terraform-apply-gated workflow runs
- Dispatches new run if none found for current HEAD
- Uses `workflow_dispatch` event with `confirm=PLAN` parameter

### Step C: Monitoring
- Waits up to 10 minutes (120 × 5sec) for workflow completion
- Verifies conclusion is "success"
- Shows failed step logs if workflow fails

### Step D: UBLA Audit
- Downloads `tfplan-text/tfplan.txt` artifact
- Scans for UBLA changes:
  - ✅ `false → true` (hardening allowed)
  - ❌ `true → false` (hardening violation)
- Fails if any `true → false` flips detected

### Step E: Evidence Creation
- Creates timestamped evidence file in `governance/`
- Commits and pushes evidence to branch
- Includes run URL, commit SHA, plan summary, UBLA audit results

### Step F: PR Management
- Posts audit summary comment on PR
- Marks PR as ready (if draft)
- Enables auto-merge with squash and branch deletion
- Shows final PR state

## Success Criteria

The script succeeds when:
- ✅ terraform-apply-gated workflow run found/dispatched
- ✅ Workflow completes with "success" status
- ✅ tfplan.txt artifact downloaded
- ✅ No UBLA `true → false` violations found
- ✅ Evidence file created and committed
- ✅ PR commented and auto-merge enabled

## Error Codes

- `10` - No PR found for current branch
- `11` - No workflow dispatch run found
- `12` - Workflow run failed (not success)
- `13` - Missing tfplan.txt artifact
- `14` - UBLA hardening violation (`true → false` detected)

## Configuration

The script is configured for:
- Repository: `Huyen1974/agent-data-test`
- Root path: `$HOME/agent-data-test`
- Workflow: `.github/workflows/terraform-apply-gated.yml`
- Artifact: `tfplan-text/tfplan.txt`

## Example Output

```
## CLI-UBLA-2d-MERGE-PR-v1 :: start
[CLI-UBLA-2d-MERGE-PR-v1:A] BR=m5/ubla-hardening-20250816T064104Z
[CLI-UBLA-2d-MERGE-PR-v1:A] PR=https://github.com/Huyen1974/agent-data-test/pull/123
[CLI-UBLA-2d-MERGE-PR-v1:B] HEAD_SHA=abc123... TS0=2025-01-16T12:34:56Z
[CLI-UBLA-2d-MERGE-PR-v1:B] RUN_ID=12345678
[CLI-UBLA-2d-MERGE-PR-v1:C] RUN=https://github.com/.../actions/runs/12345678 completed success
[CLI-UBLA-2d-MERGE-PR-v1:D] PLAN_SUMMARY: Plan: 5 to add, 3 to change, 0 to destroy
[CLI-UBLA-2d-MERGE-PR-v1:D] UBLA_FALSE_TO_TRUE=3  UBLA_TRUE_TO_FALSE=0
[CLI-UBLA-2d-MERGE-PR-v1:D] UBLA_HARDENING_OK
[CLI-UBLA-2d-MERGE-PR-v1:E] EVIDENCE_COMMITTED: governance/MERGE_EVIDENCE_UBLA_12345678_20250116T123456Z.md
[CLI-UBLA-2d-MERGE-PR-v1:F] POSTING COMMENT...
[CLI-UBLA-2d-MERGE-PR-v1:F] READY PR (if draft)...
[CLI-UBLA-2d-MERGE-PR-v1:F] ENABLE AUTO-MERGE (squash + delete-branch)...
[CLI-UBLA-2d-MERGE-PR-v1:F] FINAL PR STATE: open ready mergeable=true mstate=clean merged=false
## CLI-UBLA-2d-MERGE-PR-v1 :: done
```

## Notes

- The script uses `bash -euo pipefail` for strict error handling
- All steps are logged with unique IDs for easy tracking
- Evidence files are preserved in `governance/` directory
- Auto-merge may fail due to branch protection rules (review required)
- Apply operations remain gated - this only validates the plan
