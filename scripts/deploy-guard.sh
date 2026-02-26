#!/usr/bin/env bash
# deploy-guard.sh — VPS Deploy Guard (WEB-86C)
# Detects unauthorized docker cp/exec operations on agent-data container.
# Intended to run via cron every 5 minutes on VPS.
#
# Install on VPS:
#   cp scripts/deploy-guard.sh /opt/incomex/scripts/deploy-guard.sh
#   chmod +x /opt/incomex/scripts/deploy-guard.sh
#   crontab: */5 * * * * /opt/incomex/scripts/deploy-guard.sh >> /var/log/deploy-guard.log 2>&1
set -euo pipefail

LOG="/var/log/deploy-guard.log"
CONTAINER="incomex-agent-data"
ALERT_FILE="/tmp/deploy-guard-alert"

# Check docker events from last 6 minutes (overlap with 5m cron)
SINCE="6m"

# Look for docker cp or docker exec events on agent-data container
VIOLATIONS=$(docker events --since "${SINCE}" --until "0s" \
  --filter "container=${CONTAINER}" \
  --filter "type=container" \
  --format '{{.Action}} {{.Time}}' 2>/dev/null \
  | grep -E "^(exec_create|exec_start|copy)" || true)

if [[ -n "$VIOLATIONS" ]]; then
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$TIMESTAMP] VIOLATION DETECTED on ${CONTAINER}:"
  echo "$VIOLATIONS"
  echo "---"

  # Write alert file for external monitoring
  echo "$TIMESTAMP" > "$ALERT_FILE"
  echo "$VIOLATIONS" >> "$ALERT_FILE"

  # Optional: could send webhook/email alert here
  # curl -s -X POST "$ALERT_WEBHOOK" -d "{\"text\":\"Deploy guard violation: $VIOLATIONS\"}"
fi
