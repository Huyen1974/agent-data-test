"""Universal Resilient Caller — retry, health tracking, and startup probes.

Phonebook Pattern: Services are auto-discovered from SERVICE_{NAME}_URL env vars.
Adding a new service = adding 1 env var, no code change needed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_none,
)

logger = logging.getLogger(__name__)
# Ensure our logger has at least one handler (basicConfig may be preempted by langroid)
if not logger.handlers and not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_RETRIES = 3
DEFAULT_WAIT_MIN = 1  # seconds
DEFAULT_WAIT_MAX = 4  # seconds (1s -> 2s -> 4s)
DEFAULT_TIMEOUT = 30.0  # seconds

_TESTING = os.getenv("TESTING") == "1"


# ---------------------------------------------------------------------------
# ServiceHealthRegistry — per-service status with TTL cache
# ---------------------------------------------------------------------------
class ServiceStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: float = 0.0
    last_error: str | None = None
    latency_ms: float = 0.0
    consecutive_failures: int = 0


class ServiceHealthRegistry:
    """Tracks health status for all external services with a 30s TTL cache."""

    CACHE_TTL = 30.0

    def __init__(self) -> None:
        self._services: dict[str, ServiceHealth] = {}

    def register(self, name: str) -> None:
        if name not in self._services:
            self._services[name] = ServiceHealth(name=name)

    def mark_healthy(self, name: str, latency_ms: float = 0.0) -> None:
        svc = self._services.setdefault(name, ServiceHealth(name=name))
        svc.status = ServiceStatus.OK
        svc.last_check = time.monotonic()
        svc.last_error = None
        svc.latency_ms = latency_ms
        svc.consecutive_failures = 0

    def mark_unhealthy(self, name: str, error: str) -> None:
        svc = self._services.setdefault(name, ServiceHealth(name=name))
        svc.consecutive_failures += 1
        svc.last_check = time.monotonic()
        svc.last_error = error
        if svc.consecutive_failures >= 3:
            svc.status = ServiceStatus.DOWN
        else:
            svc.status = ServiceStatus.DEGRADED

    def get_status(self, name: str) -> ServiceHealth:
        return self._services.get(name, ServiceHealth(name=name))

    def is_cache_fresh(self, name: str) -> bool:
        svc = self._services.get(name)
        if svc is None:
            return False
        return (time.monotonic() - svc.last_check) < self.CACHE_TTL

    def summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, svc in self._services.items():
            result[name] = {
                "status": svc.status.value,
                "latency_ms": round(svc.latency_ms, 1),
                "last_error": svc.last_error,
            }
        return result

    def overall_status(self) -> str:
        if not self._services:
            return "healthy"
        statuses = [s.status for s in self._services.values()]
        if ServiceStatus.DOWN in statuses or ServiceStatus.DEGRADED in statuses:
            return "degraded"
        return "healthy"


# Module-level singleton
health_registry = ServiceHealthRegistry()


# ---------------------------------------------------------------------------
# ResilientCaller — async HTTP client with retry
# ---------------------------------------------------------------------------
RETRYABLE_HTTP_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
)

RETRYABLE_STATUS_CODES = {503, 504, 429}


class RetryableHTTPError(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {detail}")


class ResilientCaller:
    """Async HTTP client with built-in retry, timeout, and health tracking."""

    def __init__(
        self,
        *,
        service_name: str,
        base_url: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.service_name = service_name
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        health_registry.register(service_name)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers=self.headers,
            )
        return self._client

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        client = await self._ensure_client()
        wait_strategy = (
            wait_none()
            if _TESTING
            else wait_exponential(
                multiplier=1, min=DEFAULT_WAIT_MIN, max=DEFAULT_WAIT_MAX
            )
        )

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_strategy,
            retry=retry_if_exception_type(
                (*RETRYABLE_HTTP_EXCEPTIONS, RetryableHTTPError)
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            t0 = time.monotonic()
            response = await client.request(method, url, **kwargs)
            latency = (time.monotonic() - t0) * 1000

            if response.status_code in RETRYABLE_STATUS_CODES:
                health_registry.mark_unhealthy(
                    self.service_name, f"HTTP {response.status_code}"
                )
                raise RetryableHTTPError(response.status_code)

            health_registry.mark_healthy(self.service_name, latency)
            return response

        try:
            return await _do_request()
        except RETRYABLE_HTTP_EXCEPTIONS as exc:
            health_registry.mark_unhealthy(self.service_name, str(exc))
            raise
        except RetryError as exc:
            health_registry.mark_unhealthy(self.service_name, str(exc))
            raise

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def health_check(self) -> dict[str, Any]:
        """Ping the service base URL and return health status."""
        try:
            t0 = time.monotonic()
            response = await self.get("/")
            latency = (time.monotonic() - t0) * 1000
            status = "ok" if response.status_code < 500 else "down"
            if status == "ok":
                health_registry.mark_healthy(self.service_name, latency)
            else:
                health_registry.mark_unhealthy(
                    self.service_name, f"HTTP {response.status_code}"
                )
            return {
                "service": self.service_name,
                "status": status,
                "latency_ms": round(latency, 1),
            }
        except Exception as exc:
            health_registry.mark_unhealthy(self.service_name, str(exc))
            return {
                "service": self.service_name,
                "status": "down",
                "latency_ms": None,
                "error": str(exc),
            }

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# sync_retry — decorator factory for synchronous SDK calls
# ---------------------------------------------------------------------------
def sync_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    service_name: str = "",
) -> Callable:
    """Decorator factory: adds tenacity retry to sync functions.

    Used for vector_store.py methods (Qdrant SDK, OpenAI SDK).
    Retries on ConnectionError, TimeoutError, OSError.
    """
    wait_strategy = (
        wait_none()
        if _TESTING
        else wait_exponential(multiplier=1, min=DEFAULT_WAIT_MIN, max=DEFAULT_WAIT_MAX)
    )

    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_strategy,
            retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Dynamic service discovery — Phonebook Pattern
# ---------------------------------------------------------------------------
_LEGACY_MAPPINGS: dict[str, list[str]] = {
    "qdrant": ["QDRANT_URL", "QDRANT_API_URL"],
    "openai": ["OPENAI_API_URL", "OPENAI_BASE_URL"],
}

_discovered_services: dict[str, ResilientCaller] = {}


def discover_services() -> dict[str, ResilientCaller]:
    """Auto-discover services from SERVICE_{NAME}_URL env vars.

    Convention:
      SERVICE_QDRANT_URL=https://xxx.qdrant.io
      SERVICE_OPENAI_URL=https://api.openai.com/v1

    Optional per-service overrides:
      SERVICE_QDRANT_TIMEOUT=60
      SERVICE_QDRANT_RETRIES=5

    Backward compatible: falls back to legacy env vars (QDRANT_URL, etc.)
    """
    global _discovered_services
    services: dict[str, ResilientCaller] = {}
    prefix = "SERVICE_"
    suffix = "_URL"

    # 1. Scan for SERVICE_{NAME}_URL convention
    for key, value in os.environ.items():
        if key.startswith(prefix) and key.endswith(suffix) and value:
            name = key[len(prefix) : -len(suffix)].lower()
            timeout_key = f"{prefix}{name.upper()}_TIMEOUT"
            retries_key = f"{prefix}{name.upper()}_RETRIES"
            timeout = int(os.getenv(timeout_key, str(int(DEFAULT_TIMEOUT))))
            retries = int(os.getenv(retries_key, str(DEFAULT_MAX_RETRIES)))
            services[name] = ResilientCaller(
                service_name=name,
                base_url=value,
                timeout=float(timeout),
                max_retries=retries,
            )

    # 2. Backward-compatible fallback for legacy env vars
    for name, legacy_keys in _LEGACY_MAPPINGS.items():
        if name not in services:
            for legacy_key in legacy_keys:
                url = os.getenv(legacy_key, "")
                if url:
                    services[name] = ResilientCaller(service_name=name, base_url=url)
                    break

    # Register all in health registry
    for svc_name in services:
        health_registry.register(svc_name)

    _discovered_services = services
    return services


def get_discovered_services() -> dict[str, ResilientCaller]:
    return _discovered_services


# ---------------------------------------------------------------------------
# Startup probes
# ---------------------------------------------------------------------------
async def probe_qdrant() -> bool:
    from agent_data import vector_store as vs

    try:
        store = vs.get_vector_store()
        if not store.enabled:
            health_registry.register("qdrant")
            logger.info("Qdrant vector store disabled; skipping probe")
            return True
        t0 = time.monotonic()
        count = await asyncio.to_thread(store.count)
        latency = (time.monotonic() - t0) * 1000
        if count >= 0:
            health_registry.mark_healthy("qdrant", latency)
            logger.info("Qdrant probe OK: %d vectors (%.0fms)", count, latency)
            return True
        health_registry.mark_unhealthy("qdrant", "count returned -1")
        return False
    except Exception as exc:
        health_registry.mark_unhealthy("qdrant", str(exc))
        logger.warning("Qdrant probe failed: %s", exc)
        return False


async def probe_firestore() -> bool:
    try:
        from agent_data.server import agent

        db = getattr(agent, "db", None)
        if db is None:
            logger.info("Firestore not configured; skipping probe")
            return True
        t0 = time.monotonic()
        await asyncio.to_thread(lambda: list(db.collections())[:1])
        latency = (time.monotonic() - t0) * 1000
        health_registry.mark_healthy("firestore", latency)
        logger.info("Firestore probe OK (%.0fms)", latency)
        return True
    except Exception as exc:
        health_registry.mark_unhealthy("firestore", str(exc))
        logger.warning("Firestore probe failed: %s", exc)
        return False


async def probe_openai() -> bool:
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        health_registry.mark_healthy("openai", 0)
        return True
    health_registry.mark_unhealthy("openai", "OPENAI_API_KEY not set")
    return False


# ---------------------------------------------------------------------------
# Fail-fast config validation
# ---------------------------------------------------------------------------
def validate_required_env() -> None:
    """Raise RuntimeError if critical env vars missing in production."""
    env = os.getenv("APP_ENV", "").lower()
    if env != "production":
        return
    required = ["QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. Cannot start."
        )


# ---------------------------------------------------------------------------
# FastAPI lifespan context manager
# ---------------------------------------------------------------------------
@asynccontextmanager
async def resilient_lifespan(app: Any):  # noqa: ANN401
    """FastAPI lifespan: validate config, discover services, run probes."""
    logger.info("=== Resilient startup: probing external services ===")

    validate_required_env()

    # Discover services from env (Phonebook Pattern)
    services = discover_services()
    logger.info("Discovered %d service(s): %s", len(services), list(services.keys()))

    # Register well-known services that use SDK (not HTTP)
    for name in ("qdrant", "firestore", "openai"):
        health_registry.register(name)

    # Run probes concurrently
    results = await asyncio.gather(
        probe_qdrant(),
        probe_firestore(),
        probe_openai(),
        return_exceptions=True,
    )

    probe_names = ["qdrant", "firestore", "openai"]
    for name, result in zip(probe_names, results, strict=False):
        if isinstance(result, Exception):
            logger.warning("Probe %s raised: %s", name, result)

    logger.info(
        "Startup complete. Overall: %s | Services: %s",
        health_registry.overall_status(),
        health_registry.summary(),
    )

    yield

    # Cleanup: close all discovered service clients
    for caller in _discovered_services.values():
        await caller.close()
    logger.info("=== Shutdown: cleaned up resilient callers ===")
