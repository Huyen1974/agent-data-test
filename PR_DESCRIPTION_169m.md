# PR#1 "Security Verify" (M2, 169m) - Anti-Fake Reporting System

## Summary

Implements M2 security verification system with independent verification capabilities to prevent fake security reports. This PR adds comprehensive WIF and secrets validation with automated fail-fast gates and artifact generation for independent audit.

## Changes

### 🔧 Scripts
- **`scripts/verify_wif_attr.sh`** - WIF attribute verification (POSIX Bash, read-only GCP)
- **`scripts/validate_secrets_m2.py`** - GitHub secrets validation (Python 3.11, no PAT expiry check)

### 🚀 Workflow
- **`.github/workflows/security-verify.yml`** - WIF auth, scripts execution, fail-fast gate, artifacts upload, Job Summary

### 📚 Documentation
- **`SECURITY_VERIFY_README.md`** - Complete usage guide and independent verification instructions

## Key Features

✅ **WIF Verification**: Validates attribute conditions for 3 repositories (central, test, production)
✅ **Secrets Validation**: Checks required secrets and PAT authentication
✅ **Fail-Fast Gate**: Workflow fails if any boolean validation is false
✅ **Independent Verification**: Checksums and provenance for post-run audit
✅ **Comprehensive Job Summary**: All boolean values and checksums displayed
✅ **Artifacts Upload**: `wif_verify.json`, `secrets_verify.json`, `checksums.txt`, `provenance.json`

## Security Guardrails

- ✅ No secrets/PAT printed in logs
- ✅ Read-only GCP operations only
- ✅ No Terraform/Qdrant/cluster modifications
- ✅ Single-topic PR scope
- ✅ Pre-commit hooks passed

## Independent Verification Guide

**For project owners to independently verify workflow results:**

```bash
# Get latest Security Verify run ID
RID="$(gh run list --repo Huyen1974/chatgpt-githubnew --workflow='Security Verify' --limit 1 --json databaseId -q '.[0].databaseId')"
gh run watch "$RID" --repo Huyen1974/chatgpt-githubnew --exit-status
gh run download "$RID" --repo Huyen1974/chatgpt-githubnew -n security-verify -D /tmp/secv && ls -la /tmp/secv

# Verify checksums independently
cd /tmp/secv
sha256sum wif_verify.json secrets_verify.json 2>/dev/null || shasum -a 256 wif_verify.json secrets_verify.json
echo "---- checksums.txt ----"
cat checksums.txt

# Parse JSON & assert booleans
jq -r '"WIF: "+(.includes.central|tostring)+","+(.includes.test|tostring)+","+(.includes.production|tostring)+" | MAP:"+(.mapping.has_repository|tostring)+","+(.mapping.has_ref|tostring)+","+(.mapping.has_actor|tostring)+" | SA:"+(.sa_binding.central|tostring)+","+(.sa_binding.test|tostring)+","+(.sa_binding.production|tostring)' wif_verify.json
jq -r '"SECRETS central_min_ok="+(.central_min_ok|tostring)+", child_min_ok="+(.child_min_ok|tostring)+", pat_http_200="+(.pat_http_200|tostring)+", forbidden_pat_present="+(.forbidden_pat_present|tostring)' secrets_verify.json

# ALL TRUE?
jq -e '(.includes.central and .includes.test and .includes.production and .mapping.has_repository and .mapping.has_ref and .mapping.has_actor and .sa_binding.central and .sa_binding.test and .sa_binding.production)' wif_verify.json >/dev/null
jq -e '(.central_min_ok and .child_min_ok and .pat_http_200 and (.forbidden_pat_present|not))' secrets_verify.json >/dev/null && echo "INDEPENDENT_VERIFY=PASS"
```

## Definition of Done (DoD)

### Expected Results:
- [ ] Workflow succeeds without errors
- [ ] `wif_verify.json`: All `includes`/`mapping`/`sa_binding` == `true`
- [ ] `secrets_verify.json`: `central_min_ok`==`true`, `child_min_ok`==`true`, `pat_http_200`==`true`, `forbidden_pat_present`==`false`
- [ ] `checksums.txt` + `provenance.json` uploaded as artifacts
- [ ] Job Summary displays all boolean values + checksums
- [ ] Independent CLI verification returns `INDEPENDENT_VERIFY=PASS`

### Test Plan:
1. Manual trigger Security Verify workflow
2. Verify all steps complete successfully
3. Download artifacts and run independent verification
4. Confirm Job Summary shows all green checkmarks

## Technical Details

### WIF Verification Logic:
- Constructs provider path: `projects/{PN}/locations/global/workloadIdentityPools/{WIF_POOL}/providers/{WIF_PROVIDER_NAME}`
- Checks attribute conditions include all 3 repositories
- Validates required attribute mappings (repository, ref, actor)
- Verifies SA IAM bindings for workloadIdentityUser role

### Secrets Validation Logic:
- Tests PAT authentication via GitHub API `/user` endpoint
- Lists repository secrets via GitHub REST API
- Validates presence of 4 required secrets: `GCP_PROJECT_ID`, `GCP_SERVICE_ACCOUNT`, `GCP_WIF_POOL`, `GCP_WIF_PROVIDER`
- Checks child repository has no PAT secrets (case-insensitive)

### Workflow Features:
- WIF authentication with hardened provider
- Fail-fast gate with comprehensive boolean validation
- SHA256 checksums for tamper detection
- ISO8601 timestamped provenance
- Detailed Job Summary with status icons
- 30-day artifact retention

---
**Commit:** `security: add WIF & secrets verify workflow (M2, 169m)`
**Branch:** `docs/p167a-rules-lossless-20250809-101205`
**Files:** 4 new files (scripts, workflow, README, PR description)
