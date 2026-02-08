# Agent Data — Commercial Certification Report

**Date:** 2026-02-08
**Revision:** `agent-data-test-00060-gmz`
**Commit:** `d83461d` (PR #244 — Vector Auto-Heal)
**Environment:** Production (Cloud Run, asia-southeast1)
**Service URL:** `https://agent-data-test-pfne2mqwja-as.a.run.app`

---

## Part 1 — Merge Result

| Item | Value |
|------|-------|
| PR | #244 — feat: Vector Auto-Heal — self-recovery on audit-sync |
| CI Status | 20/20 GREEN |
| Merge Commit | `d83461d` |
| Branch | main (clean) |
| Method | Squash merge (admin) |

## Part 2 — Auto-Deploy Result

| Item | Value |
|------|-------|
| Workflow | `cloudrun-cd.yml` (triggered on push to main) |
| Run | #21799304447 |
| Duration | 4m43s |
| Previous Revision | `agent-data-test-00059-fwl` |
| New Revision | `agent-data-test-00060-gmz` |
| Status | SUCCESS — all steps passed |

## Part 3 — Certification Test Results

| # | Test | Method | Result | Details |
|---|------|--------|--------|---------|
| 1 | Health + data_integrity | `GET /health` | PASS | `status: healthy`, `data_integrity.sync_status: ok`, 106 docs, 315 vectors |
| 2 | CRUD: create document | `POST /documents` | PASS | `docs/test/cert-test-244` created, revision 1 |
| 3 | Search: find created doc | `POST /mcp/tools/search_knowledge` | PASS | Top result: `cert-test-244`, score 0.538 |
| 4 | Update: modify content | `PUT /documents/{id}` | PASS | Updated to revision 2, content changed |
| 5 | Search: confirm vector updated | `POST /mcp/tools/search_knowledge` | PASS | Top result: `cert-test-244`, score 0.598, shows UPDATED content |
| 6 | Audit: check sync status | `POST /kb/audit-sync` | PASS | 107 docs, 316 vectors, 0 orphans, 2 known empty ghosts |
| 7 | Auto-heal run | `POST /kb/audit-sync {"auto_heal": true}` | PASS | `auto_heal: true` in response, reindex attempted 2 empty docs (skipped_empty), 0 orphans |
| 8 | Delete: remove test doc | `DELETE /documents/{id}` | PASS | `cert-test-244` deleted, revision 3 |
| 9 | Audit: no orphan vectors | `POST /kb/audit-sync` | PASS | 106 docs, 315 vectors, 0 orphans — vectors cleaned on delete |
| 10 | Cloud Scheduler active | `gcloud scheduler jobs describe` | PASS | `vector-audit-sync-6h` ENABLED, schedule `0 */12 * * *`, auto_heal=true |
| 11 | Monitoring alert active | `gcloud monitoring policies list` | PASS | `Vector Monitoring Endpoint Failures` ENABLED, 5xx threshold |

**Result: 11/11 PASS**

---

## End-to-End Lifecycle Proof

```
CREATE doc → vectors indexed (score 0.538)
  → UPDATE content → vectors re-synced (score 0.598, new content)
    → AUDIT → 0 orphans, 0 new ghosts
      → AUTO-HEAL → attempted fix on 2 known empty archive docs
        → DELETE doc → vectors cleaned
          → AUDIT → 0 orphans confirmed
```

The full document lifecycle (create → search → update → search → delete → audit) works correctly on production. Vectors stay synchronized at every step.

## Known Issues

| Issue | Severity | Notes |
|-------|----------|-------|
| 2 ghost documents | Low | `docs/archive/move-dest-w53.md` and `docs/archive/move-sync-dest.md` — empty archive docs with no content to index. Auto-heal correctly reports `skipped_empty`. Not a sync error. |

## Infrastructure Summary

| Component | Status |
|-----------|--------|
| Cloud Run (revision 00060) | Serving |
| CI/CD Pipeline (cloudrun-cd.yml) | Auto-deploys on push to main |
| Cloud Scheduler (12h auto-heal) | ENABLED |
| Monitoring Alert (5xx) | ENABLED |
| Qdrant Vector Store | 315 vectors, healthy |
| Firestore | 106 documents, healthy |
