"""Helpers for accessing Google Secret Manager using ADC credentials."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

try:  # pragma: no cover - optional dependency
    from google.api_core import exceptions as gcloud_exceptions  # type: ignore
    from google.cloud import secretmanager  # type: ignore
    _IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - library not installed
    secretmanager = None  # type: ignore
    gcloud_exceptions = None  # type: ignore
    _IMPORT_ERROR = exc


class SecretAccessError(RuntimeError):
    """Raised when a secret cannot be accessed."""


def _resolve_project_id(project_id: Optional[str] = None) -> str:
    for candidate in (
        project_id,
        os.getenv("GOOGLE_CLOUD_PROJECT"),
        os.getenv("GCP_PROJECT"),
        os.getenv("PROJECT_ID"),
    ):
        if candidate:
            return candidate
    raise SecretAccessError(
        "Secret Manager project ID not configured; set GOOGLE_CLOUD_PROJECT or PROJECT_ID"
    )


@lru_cache(maxsize=1)
def _client():
    if secretmanager is None:  # pragma: no cover - optional dependency guard
        detail = f" ({_IMPORT_ERROR})" if _IMPORT_ERROR else ""
        raise SecretAccessError(
            "google-cloud-secret-manager is not installed; run `pip install google-cloud-secret-manager`" + detail
        )
    return secretmanager.SecretManagerServiceClient()


def _build_resource_name(secret_name: str, project_id: Optional[str], version: str) -> str:
    if secret_name.startswith("projects/"):
        if "/versions/" in secret_name:
            return secret_name
        return f"{secret_name}/versions/{version}"
    project = _resolve_project_id(project_id)
    if secret_name.count("/") >= 2:
        # Full resource without version but with project embedded (e.g. projects/x/secrets/y)
        base = secret_name
        if "/versions/" in base:
            return base
        return f"{base}/versions/{version}"
    return f"projects/{project}/secrets/{secret_name}/versions/{version}"


@lru_cache(maxsize=128)
def get_secret(
    secret_name: str,
    *,
    project_id: Optional[str] = None,
    version: str = "latest",
) -> str:
    """Return secret payload as text using Application Default Credentials."""
    name = _build_resource_name(secret_name, project_id, version)
    try:
        response = _client().access_secret_version(name=name)
    except SecretAccessError:
        raise
    except Exception as exc:  # pragma: no cover - relies on network/library
        if gcloud_exceptions and isinstance(exc, gcloud_exceptions.NotFound):
            raise SecretAccessError(f"Secret '{secret_name}' not found") from exc
        if gcloud_exceptions and isinstance(exc, gcloud_exceptions.GoogleAPICallError):
            raise SecretAccessError(f"Failed to access secret '{secret_name}': {exc}") from exc
        raise SecretAccessError(f"Failed to access secret '{secret_name}': {exc}") from exc
    return response.payload.data.decode("utf-8")


def clear_secret_cache() -> None:
    """Clear cached client and secret responses (useful for tests)."""
    _client.cache_clear()
    get_secret.cache_clear()
