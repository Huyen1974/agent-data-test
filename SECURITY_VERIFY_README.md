# Security Verify M2 - Anti-Fake Reporting System

## Overview

This M2 Security Verification system provides independent verification of:
- Workload Identity Federation (WIF) attribute configuration
- GitHub repository secrets validation
- Protection against fake security reports through independent verification

## Components

### 1. WIF Attributes Verification (`scripts/verify_wif_attr.sh`)

Verifies WIF configuration for 3 repositories with proper attribute conditions and SA bindings.

**Environment Variables:**
- `PROJ` - GCP Project ID (default: github-chatgpt-ggcloud)
- `PN` - Project Number (default: 812872501910)
- `WIF_POOL` - WIF Pool name (default: agent-data-pool)
- `WIF_PROVIDER_NAME` - WIF Provider name (default: github-provider)

**Usage:**
```bash
bash scripts/verify_wif_attr.sh
```

### 2. Secrets Validation (`scripts/validate_secrets_m2.py`)

Validates GitHub repository secrets configuration and PAT authentication.

**Requirements:**
- Python 3.11+
- requests library
- Valid GitHub PAT

**Usage:**
```bash
python scripts/validate_secrets_m2.py \
  --central Huyen1974/chatgpt-githubnew \
  --child Huyen1974/agent-data-test \
  --pat-file pat.txt
```

### 3. Security Verify Workflow (`.github/workflows/security-verify.yml`)

Automated workflow that:
- Authenticates via WIF
- Runs both verification scripts
- Implements fail-fast gate
- Generates checksums and provenance
- Creates comprehensive Job Summary
- Uploads verification artifacts

**Manual Trigger:**
```bash
gh workflow run "Security Verify" --repo Huyen1974/chatgpt-githubnew
```

## Independent Post-Run Verification

After workflow completion, project owners can independently verify results:

```bash
# Get latest Security Verify run ID
RID="$(gh run list --repo Huyen1974/chatgpt-githubnew --workflow='Security Verify' --limit 1 --json databaseId -q '.[0].databaseId')"

# Watch run and download artifacts
gh run watch "$RID" --repo Huyen1974/chatgpt-githubnew --exit-status
gh run download "$RID" --repo Huyen1974/chatgpt-githubnew -n security-verify -D /tmp/secv && ls -la /tmp/secv

# Verify checksums independently
cd /tmp/secv
sha256sum wif_verify.json secrets_verify.json 2>/dev/null || shasum -a 256 wif_verify.json secrets_verify.json
echo "---- checksums.txt ----"
cat checksums.txt

# Parse and verify all booleans
jq -r '"WIF: "+(.includes.central|tostring)+","+(.includes.test|tostring)+","+(.includes.production|tostring)+" | MAP:"+(.mapping.has_repository|tostring)+","+(.mapping.has_ref|tostring)+","+(.mapping.has_actor|tostring)+" | SA:"+(.sa_binding.central|tostring)+","+(.sa_binding.test|tostring)+","+(.sa_binding.production|tostring)' wif_verify.json

jq -r '"SECRETS central_min_ok="+(.central_min_ok|tostring)+", child_min_ok="+(.child_min_ok|tostring)+", pat_http_200="+(.pat_http_200|tostring)+", forbidden_pat_present="+(.forbidden_pat_present|tostring)' secrets_verify.json

# Verify ALL TRUE
jq -e '(.includes.central and .includes.test and .includes.production and .mapping.has_repository and .mapping.has_ref and .mapping.has_actor and .sa_binding.central and .sa_binding.test and .sa_binding.production)' wif_verify.json >/dev/null

jq -e '(.central_min_ok and .child_min_ok and .pat_http_200 and (.forbidden_pat_present|not))' secrets_verify.json >/dev/null && echo "INDEPENDENT_VERIFY=PASS"
```

## Expected Output Format

### WIF Verification (`wif_verify.json`)
```json
{
  "prov": "projects/812872501910/locations/global/workloadIdentityPools/agent-data-pool/providers/github-provider",
  "includes": {
    "central": true,
    "test": true,
    "production": true
  },
  "mapping": {
    "has_repository": true,
    "has_ref": true,
    "has_actor": true
  },
  "sa_binding": {
    "central": true,
    "test": true,
    "production": true
  },
  "timestamp_utc": "2024-01-15T10:30:45.123Z"
}
```

### Secrets Validation (`secrets_verify.json`)
```json
{
  "central_min_ok": true,
  "child_min_ok": true,
  "pat_http_200": true,
  "forbidden_pat_present": false,
  "timestamp_utc": "2024-01-15T10:30:45.123Z"
}
```

## Definition of Done (DoD)

✅ Workflow succeeds
✅ `wif_verify.json`: All includes/mapping/sa_binding == true
✅ `secrets_verify.json`: central_min_ok==true, child_min_ok==true, pat_http_200==true, forbidden_pat_present==false
✅ `checksums.txt` and `provenance.json` uploaded
✅ Job Summary displays all boolean values and checksums
✅ Independent CLI verification passes with `INDEPENDENT_VERIFY=PASS`

## Security Guardrails

- No secrets/PAT tokens are printed in logs
- No force-push allowed
- Single-topic PR scope
- No Terraform/Qdrant/cluster modifications
- Read-only GCP operations only

## Troubleshooting

**Common Issues:**
1. **WIF Authentication Failed**: Check WIF provider configuration and SA bindings
2. **PAT Authentication Failed**: Verify PAT token has required repository permissions
3. **Missing Secrets**: Ensure all 4 required secrets are present in repositories
4. **Forbidden PAT Found**: Remove any PAT secrets from child repositories

**Debug Commands:**
```bash
# Test WIF locally (requires auth)
gcloud auth application-default login
bash scripts/verify_wif_attr.sh

# Test secrets validation locally
python scripts/validate_secrets_m2.py --central REPO1 --child REPO2 --pat-file pat.txt
```

---

*Generated for Prompt 169m - PR#1 "Security Verify" (M2, anti-fake reporting)*
