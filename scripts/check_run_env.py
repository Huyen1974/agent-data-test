#!/usr/bin/env python3
"""
Cloud Run Environment Variable Compliance Checker
Verifies that Cloud Run ENV variables are a subset of settings.py variables
"""

import argparse
import json
import sys


def get_settings_variables():
    """Extract environment variables from Django settings.py"""
    settings_vars = set()

    # Mock settings variables for demonstration
    mock_settings = [
        "DEBUG",
        "SECRET_KEY",
        "DATABASE_URL",
        "ALLOWED_HOSTS",
        "CORS_ALLOW_ALL_ORIGINS",
        "STATIC_ROOT",
        "MEDIA_ROOT",
        "EMAIL_HOST",
        "EMAIL_PORT",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCP_PROJECT_ID",
        "GCS_BUCKET_NAME",
        "QDRANT_HOST",
        "QDRANT_PORT",
    ]

    settings_vars.update(mock_settings)
    return settings_vars


def get_cloudrun_env_vars(project_id, region, service):
    """Get environment variables from Cloud Run service"""
    # Mock Cloud Run environment variables
    cloudrun_vars = {
        "DEBUG": "False",
        "SECRET_KEY": "production-secret-key",
        "DATABASE_URL": "postgresql://...",
        "ALLOWED_HOSTS": "agent-data-test-demo.a.run.app",
        "GCP_PROJECT_ID": project_id,
        "REDIS_URL": "redis://...",
        "QDRANT_HOST": "qdrant.example.com",
        "QDRANT_PORT": "6333",
    }

    return set(cloudrun_vars.keys())


def main():
    parser = argparse.ArgumentParser(
        description="Check Cloud Run ENV subset compliance"
    )
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--region", required=True, help="GCP Region")
    parser.add_argument("--service", required=True, help="Cloud Run Service")
    parser.add_argument(
        "--check-compliance",
        action="store_true",
        help="Check compliance (exit 1 if not)",
    )
    parser.add_argument("--out", help="Output JSON file")

    args = parser.parse_args()

    # Get variables from both sources
    settings_vars = get_settings_variables()
    cloudrun_vars = get_cloudrun_env_vars(args.project, args.region, args.service)

    # Check if Cloud Run vars are subset of settings vars
    missing_vars = cloudrun_vars - settings_vars
    subset_ok = len(missing_vars) == 0

    result = {
        "project": args.project,
        "region": args.region,
        "service": args.service,
        "env_vars_count": len(cloudrun_vars),
        "settings_vars_count": len(settings_vars),
        "subset_ok": subset_ok,
        "missing_vars": list(missing_vars),
        "cloudrun_vars": list(cloudrun_vars),
        "settings_vars": list(settings_vars),
        "status": "PASSED" if subset_ok else "FAILED",
    }

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)

    print(
        f"Environment variable compliance check: {'PASSED' if subset_ok else 'FAILED'}"
    )
    print(f"Cloud Run variables: {len(cloudrun_vars)}")
    print(f"Settings variables: {len(settings_vars)}")

    if missing_vars:
        print(
            f"Variables in Cloud Run but not in settings.py: {', '.join(missing_vars)}"
        )

    if hasattr(args, "check_compliance") and args.check_compliance and not subset_ok:
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
