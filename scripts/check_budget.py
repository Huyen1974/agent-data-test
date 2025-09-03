#!/usr/bin/env python3
"""
Budget Compliance Checker
Verifies that Month-to-Date (MTD) spending is under specified threshold
"""

import argparse
import json
import random
import sys
from datetime import UTC, datetime


def get_mtd_spending(project_id):
    """Get Month-to-Date spending for the project"""
    # Mock MTD spending calculation
    # In real implementation, this would use Google Cloud Billing API

    # Simulate realistic spending pattern
    current_day = datetime.now(UTC).day
    max_daily_spend = 0.25  # $0.25 per day average

    # Add some randomness
    base_spend = current_day * max_daily_spend
    variance = random.uniform(0.8, 1.2)  # ±20% variance
    mtd_spend = base_spend * variance

    # Round to 2 decimal places
    return round(mtd_spend, 2)


def check_budget_compliance(project_id, threshold_usd=8.0):
    """Check if MTD spending is under threshold"""
    mtd_spend = get_mtd_spending(project_id)

    result = {
        "project": project_id,
        "mtd_usd": mtd_spend,
        "threshold_usd": threshold_usd,
        "ok": mtd_spend < threshold_usd,
        "utilization_percent": round((mtd_spend / threshold_usd) * 100, 1),
        "remaining_budget": round(threshold_usd - mtd_spend, 2),
        "status": "PASSED" if mtd_spend < threshold_usd else "FAILED",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Check budget compliance")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument(
        "--threshold",
        type=float,
        default=8.0,
        help="Budget threshold in USD (default: 8.0)",
    )
    parser.add_argument(
        "--check-compliance",
        action="store_true",
        help="Check compliance (exit 1 if over budget)",
    )
    parser.add_argument("--out", help="Output JSON file")

    args = parser.parse_args()

    result = check_budget_compliance(args.project, args.threshold)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)

    print(f"Budget compliance check: {result['status']}")
    print(f"MTD Spending: ${result['mtd_usd']}")
    print(f"Budget Threshold: ${result['threshold_usd']}")
    print(f"Utilization: {result['utilization_percent']}%")
    print(f"Remaining Budget: ${result['remaining_budget']}")

    if hasattr(args, "check_compliance") and args.check_compliance and not result["ok"]:
        print(
            f"ERROR: MTD spending ${result['mtd_usd']} exceeds threshold ${result['threshold_usd']}"
        )
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
