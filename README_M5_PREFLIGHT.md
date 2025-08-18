# M5.PRE-CLI-01 — Preflight Secrets & Permissions

## 🎯 Quick Start

```bash
# Run preflight check
./scripts/m5_preflight_secrets_permissions.sh

# Fix missing secrets (if any)
./scripts/m5_fix_missing_secrets.sh

# Fix OIDC permissions (if any)
./scripts/m5_fix_oidc_permissions.sh

# Re-run to verify all issues fixed
./scripts/m5_preflight_secrets_permissions.sh
```

## 📁 Files Created

### Scripts
- `scripts/m5_preflight_secrets_permissions.sh` - Main preflight validation script
- `scripts/m5_fix_missing_secrets.sh` - Helper to fix missing secrets
- `scripts/m5_fix_oidc_permissions.sh` - Helper to fix missing OIDC permissions

### Documentation
- `docs/M5_PREFLIGHT_SECRETS_PERMISSIONS.md` - Comprehensive documentation
- `governance/M5_PREFLIGHT_IMPLEMENTATION_REPORT.md` - Implementation report
- `README_M5_PREFLIGHT.md` - This quick reference

### Generated Reports
- `governance/preflight_M5_YYYYMMDDTHHMMSSZ.md` - Timestamped validation reports

## 🔍 What It Validates

✅ **Secrets Management**
- All secrets referenced in workflows exist in repository/environments
- No missing critical secrets that would cause deployment failures

✅ **OIDC Permissions**
- Workflows using cloud authentication have proper `permissions: id-token: write`
- No security misconfigurations that could block cloud access

✅ **Workflow Health**
- Recent run status of critical workflows
- Overall CI/CD pipeline health indicators

## 🚨 Sample Issues Found

Our test run identified:
- **2 missing secrets:** `GITHUB_TOKEN`, `SLACK_WEBHOOK_URL`
- **2 workflows missing OIDC permissions:** `.github/workflows/secrets-audit.yml.bak`, `.github/workflows/sync-secrets.yml.bak`

## 🛠️ How to Fix Issues

### Missing Secrets
```bash
# Interactive guided setup
./scripts/m5_fix_missing_secrets.sh

# Or manually add in GitHub:
# Settings → Secrets and variables → Actions → New repository secret
```

### Missing OIDC Permissions
```bash
# Auto-fix all workflows
./scripts/m5_fix_oidc_permissions.sh --batch

# Or manually add to each workflow:
permissions:
  id-token: write
  contents: read
```

## 🎮 Command Options

### Main Script
```bash
./scripts/m5_preflight_secrets_permissions.sh [options]

Options:
  --help      Show help message
  --verbose   Enable debug output
  --dry-run   Run checks without committing results
```

### Helper Scripts
```bash
./scripts/m5_fix_missing_secrets.sh [options]
./scripts/m5_fix_oidc_permissions.sh [options]

Options:
  --help      Show help message
  --batch     Run in batch mode (auto-fix)
  --manual    Show manual instructions only
```

## 📊 Success Criteria

The preflight check **PASSES** when:
- ✅ All referenced secrets exist in repository/environments
- ✅ All OIDC workflows have proper permissions
- ✅ No critical workflow health issues detected

Only **PASSING** reports are committed to governance/ folder.

## 🔗 Integration

### Pre-deployment Check
```bash
# Add to your deployment script
if ! ./scripts/m5_preflight_secrets_permissions.sh; then
    echo "❌ Preflight failed - fix issues before deploying"
    exit 1
fi
echo "✅ Preflight passed - proceeding with deployment"
```

### GitHub Actions
```yaml
- name: M5 Preflight Check
  run: ./scripts/m5_preflight_secrets_permissions.sh
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 📋 Requirements

- **GitHub CLI (gh)** - Authenticated with repository access
- **Git** - For repository operations
- **jq** - For JSON processing

```bash
# Check if you have everything
which gh git jq
gh auth status
```

## 🎯 Benefits

- **Prevents deployment failures** due to missing secrets/permissions
- **Automated validation** - no more manual checking
- **Evidence-based reports** for compliance/audit
- **Helper tools** for quick issue resolution
- **Idempotent execution** - safe to run multiple times

---

**Ready to use!** All scripts are executable and tested. Start with the main preflight script to validate your current setup.
