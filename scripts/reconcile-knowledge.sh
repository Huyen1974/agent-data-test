#!/bin/bash
# Wrapper to run reconcile-knowledge.py inside the agent-data container
# Usage: reconcile-knowledge.sh [--dry-run]
# Cron: 0 */6 * * *  /opt/incomex/scripts/reconcile-knowledge.sh >> /var/log/reconcile-knowledge.log 2>&1
docker cp /opt/incomex/scripts/reconcile-knowledge.py incomex-agent-data:/tmp/reconcile-knowledge.py
docker exec incomex-agent-data python3 /tmp/reconcile-knowledge.py "$@"
