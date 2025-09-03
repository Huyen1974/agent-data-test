#!/usr/bin/env bash
# Wrapper: calls SoT
set -euo pipefail
exec bash "$(dirname "$0")/../bootstrap/bin/sop_bootstrap_check.sh" "$@"
