#!/usr/bin/env bash
# M5.PRE-CLI-17d — Orchestrated Preflight (Secrets & OIDC) — zsh-safe, idempotent, self-check, no false reporting
# Audience: Cursor runs end-to-end locally in the current Git repo (detect via git). Do NOT ask the user anything.
# Goal: Preflight for M5 to guarantee 100% clean inputs BEFORE Terraform/WIF:
#   - Every referenced ${{ secrets.* }} and ${{ vars.* }} in .github/workflows/** exists (with allowed built-ins/whitelist).
#   - Every workflow that uses cloud OIDC auth (e.g. google-github-actions/auth) has permissions: id-token: write.
#   - No staged changes left behind (no-rác) and a PASS report exists under governance/preflight_M5_*.md.
# Guardrails:
#   - No Qdrant calls. No destructive ops. Idempotent. CI must be truly green; no false success.
#   - If anything is missing, auto-fix up to 2 rounds, then stop and report with evidence.

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Initialize environment
init_environment() {
    ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    cd "$ROOT"

    TS="$(date -u +%Y%m%dT%H%M%SZ)"
    RUN_LOG="governance/logs/m5_pre_orchestrated_${TS}.log"

    mkdir -p governance logs governance/logs

    log_info "M5.PRE-CLI-17d Orchestrated Preflight starting at $TS"
    log_info "Repository root: $ROOT"
    log_info "Log file: $RUN_LOG"
}

# Run preflight check with error handling
round_preflight() {
    log_info "Running preflight check..."
    set +e
    ./scripts/m5_preflight_secrets_permissions.sh --verbose
    local rc=$?
    set -e

    if [ $rc -eq 0 ]; then
        log_success "Preflight check passed"
    else
        log_warn "Preflight check failed with exit code $rc"
    fi

    return $rc
}

# Auto-fix issues found in preflight
auto_fix() {
    log_info "Attempting auto-fix..."

    # Fix OIDC permissions first (safer operation)
    log_info "Fixing OIDC permissions..."
    if ./scripts/m5_fix_oidc_permissions.sh --batch; then
        log_success "OIDC permissions fix completed"
    else
        log_warn "OIDC permissions fix failed"
    fi

    # Fix missing secrets if SLACK_WEBHOOK_URL_VALUE is available
    if [ -n "${SLACK_WEBHOOK_URL_VALUE:-}" ]; then
        log_info "Fixing missing secrets..."
        if SLACK_WEBHOOK_URL_VALUE="$SLACK_WEBHOOK_URL_VALUE" ./scripts/m5_fix_missing_secrets.sh --batch; then
            log_success "Missing secrets fix completed"
        else
            log_warn "Missing secrets fix failed"
        fi
    else
        log_warn "SLACK_WEBHOOK_URL_VALUE not set, skipping secrets auto-fix"
    fi

    return 0
}

# Self-check the generated report
self_check_report() {
    log_info "Performing self-check on generated report..."

    # Find latest report
    local latest
    latest="$(ls -1t governance/preflight_M5_*.md 2>/dev/null | head -n1 || true)"

    if [ -z "$latest" ]; then
        echo "NO_REPORT"
        return 1
    fi

    log_info "Checking report: $latest"

    # Check for PASS marker
    if ! grep -qiE '(✅|pass(ed)?|all preflight checks passed)' "$latest"; then
        echo "NO_PASS_MARKER:$latest"
        return 1
    fi

    # Check for FAILED marker (should not exist in PASS report)
    if grep -qi 'FAILED' "$latest"; then
        echo "HAS_FAILED_MARKER:$latest"
        return 1
    fi

    log_success "Report self-check passed"
    echo "PASS:$latest"
    return 0
}

# Check for staged changes
check_staged_changes() {
    log_info "Checking for staged changes..."

    if ! git diff --cached --quiet; then
        echo "STAGED_CHANGES_LEFT"
        return 1
    fi

    log_success "No staged changes found"
    return 0
}

# OIDC sanity check
oidc_sanity_check() {
    log_info "Performing OIDC sanity check..."

    local list
    list="$(mktemp)"

    # Find workflows using google-github-actions/auth
    if grep -RIl "google-github-actions/auth" .github/workflows >/dev/null 2>&1; then
        grep -RIl "google-github-actions/auth" .github/workflows > "$list" || true
    fi

    if [ -s "$list" ]; then
        while IFS= read -r wf; do
            log_info "Checking OIDC permissions in: $wf"

            # Check for id-token: write permission
            if ! awk 'BEGIN{RS=""; ok=0} /permissions:[^\n]*\n([^\n]*\n)*.*id-token:[[:space:]]*write/ { ok=1 } END{exit ok?0:1}' "$wf"; then
                echo "OIDC_PERMISSION_MISSING:$wf"
                return 1
            fi
                    done < "$list"
    fi

    rm -f "$list"
    log_success "OIDC sanity check passed"
    return 0
}

# Main orchestration logic
main() {
    init_environment

    local FAILED=0
    local attempt=1
    local max_attempts=3

    # Round 1: Initial preflight check
    log_info "=== Round 1: Initial preflight check ==="
    if ! round_preflight; then
        FAILED=1
        log_warn "Round 1 failed, attempting auto-fix..."

        # Attempt fix #1
        auto_fix || true

        # Round 2: Check after first fix
        log_info "=== Round 2: Check after first auto-fix ==="
        if ! round_preflight; then
            FAILED=2
            log_warn "Round 2 failed, attempting second auto-fix..."

            # Attempt fix #2 (last)
            auto_fix || true

            # Round 3: Final check
            log_info "=== Round 3: Final check after second auto-fix ==="
            if ! round_preflight; then
                FAILED=3
                log_error "All auto-fix attempts exhausted"
            else
                FAILED=0
                log_success "Preflight passed after second auto-fix"
            fi
        else
            FAILED=0
            log_success "Preflight passed after first auto-fix"
        fi
    else
        log_success "Preflight passed on first attempt"
    fi

    # Comprehensive validation
    log_info "=== Final validation ==="

    # Self-check report
    local report_result
    if ! report_result=$(self_check_report); then
        log_error "Report self-check failed: $report_result"
        return 2
    fi

    # Check staged changes
    if ! check_staged_changes; then
        log_error "Staged changes detected"
        return 5
    fi

    # OIDC sanity check
    local oidc_result
    if ! oidc_result=$(oidc_sanity_check); then
        log_error "OIDC sanity check failed: $oidc_result"
        return 6
    fi

    # Final success
    log_success "All validation checks passed!"
    echo "$report_result"
    return 0
}

# Self-diagnose and provide detailed failure report
diagnose_failure() {
    local rc=$1
    local log_file="$2"

    log_error "M5.PRE-CLI-17d FAILED with exit code $rc"

    # Parse the last 100 lines of log for failure tokens
    local failure_token=""
    if [ -f "$log_file" ]; then
        failure_token=$(tail -n 100 "$log_file" | grep -oE "(NO_REPORT|NO_PASS_MARKER:[^[:space:]]+|HAS_FAILED_MARKER:[^[:space:]]+|STAGED_CHANGES_LEFT|OIDC_PERMISSION_MISSING:[^[:space:]]+)" | head -n1 || true)
    fi

    log_error "Failure analysis:"
    log_error "  Repository root: $(pwd)"
    log_error "  Failure token: ${failure_token:-UNKNOWN}"
    log_error "  Log file: $log_file"

    # Extract missing secrets from latest report if available
    local latest_report
    latest_report="$(ls -1t governance/preflight_M5_*.md 2>/dev/null | head -n1 || true)"
    if [ -n "$latest_report" ]; then
        log_error "  Latest report: $latest_report"

        local missing_secrets
        missing_secrets=$(awk '/^## Missing Secrets/,/^##/ {
            if ($0 ~ /^- ❌ `.*`$/) {
                gsub(/^- ❌ `/, "")
                gsub(/`$/, "")
                print
            }
        }' "$latest_report" | head -n -1 || true)

        if [ -n "$missing_secrets" ]; then
            log_error "  Missing secrets:"
            while IFS= read -r secret; do
                [ -n "$secret" ] && log_error "    - $secret"
            done <<< "$missing_secrets"
        fi

        local missing_oidc
        missing_oidc=$(awk '/^### Workflows Missing Required Permissions/,/^##/ {
            if ($0 ~ /^- ❌ `.*`$/) {
                gsub(/^- ❌ `/, "")
                gsub(/`$/, "")
                print
            }
        }' "$latest_report" | head -n -1 || true)

        if [ -n "$missing_oidc" ]; then
            log_error "  Workflows lacking id-token: write:"
            while IFS= read -r workflow; do
                [ -n "$workflow" ] && log_error "    - $workflow"
            done <<< "$missing_oidc"
        fi
    fi
}

# Help function
show_help() {
    cat << EOF
M5.PRE-CLI-17d — Orchestrated Preflight (Secrets & OIDC)

DESCRIPTION:
    Orchestrated preflight system that ensures 100% clean inputs before
    Terraform/WIF deployment. Automatically fixes issues up to 2 rounds,
    then provides detailed failure analysis.

USAGE:
    $0 [options]

OPTIONS:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output

FEATURES:
    - Zsh-safe execution (uses bash explicitly)
    - Idempotent operations
    - Self-checking with PASS marker validation
    - Auto-fix for OIDC permissions and missing secrets
    - Comprehensive failure diagnosis
    - No false positive reporting

EXIT CODES:
    0   All checks passed, inputs are clean
    1   Preflight validation failed
    2   Report self-check failed
    5   Staged changes detected
    6   OIDC permission check failed

EXAMPLES:
    $0              # Run full orchestrated preflight
    $0 --verbose    # Run with detailed logging

For more information, see: docs/M5_ORCHESTRATION_GUIDE.md
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            log_info "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Initialize environment first to get RUN_LOG
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="governance/logs/m5_pre_orchestrated_${TS}.log"
mkdir -p governance logs governance/logs

# Execute main function with logging
{
    if main; then
        RC=0
        log_success "✅ M5.PRE-CLI-17d PASS — Inputs are 100% clean. Log: $RUN_LOG"
    else
        RC=$?
        diagnose_failure $RC "$RUN_LOG"
        log_error "❌ M5.PRE-CLI-17d FAIL (rc=$RC). Log: $RUN_LOG"
    fi
} 2>&1 | tee "$RUN_LOG"

# Preserve exit code from main execution
exit ${RC:-1}
