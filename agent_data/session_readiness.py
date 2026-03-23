"""Session readiness gate for Agent Data transports.

Provides a thin, reusable gate that can be applied before a new session starts
real work. The gate performs:
1. backend health check
2. session binding check
3. sentinel query check
4. retry with fixed backoff (0s, 2s, 5s, 10s)
5. structured incident logging
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = (0, 2, 5, 10)
DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("SESSION_READY_CACHE_TTL_SECONDS", "600"))

CLASS_BACKEND_DOWN = "backend_down"
CLASS_TOOL_ROUTE_DOWN = "tool_route_down"
CLASS_SESSION_BINDING_FAILED = "session_binding_failed"


@dataclass(slots=True)
class SessionGateError(RuntimeError):
    """Typed failure raised by readiness callbacks."""

    classification: str
    failure_stage: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class SessionReadinessResult:
    """Serializable readiness result."""

    ready: bool
    status: str
    session_id: str
    agent: str
    transport: str
    attempts: int
    failure_stage: str | None = None
    classification: str | None = None
    error: str | None = None
    sentinel_hits: int = 0
    latency_ms: int = 0
    cached: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SessionReadinessGate:
    """Small synchronous gate with retry, cache, and incident logging."""

    def __init__(
        self,
        *,
        health_check: Callable[[], dict[str, Any] | None],
        bind_session: Callable[[str], dict[str, Any] | None],
        sentinel_check: Callable[[], dict[str, Any] | None],
        sleep_fn: Callable[[float], None] = time.sleep,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        backoff_seconds: tuple[int, ...] = BACKOFF_SECONDS,
    ) -> None:
        self.health_check = health_check
        self.bind_session = bind_session
        self.sentinel_check = sentinel_check
        self.sleep_fn = sleep_fn
        self.ttl_seconds = ttl_seconds
        self.backoff_seconds = backoff_seconds
        self._cache: dict[str, tuple[float, SessionReadinessResult]] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def ensure_ready(
        self,
        *,
        session_id: str,
        agent: str,
        transport: str,
        request_id: str | None = None,
    ) -> SessionReadinessResult:
        cached = self._get_cached(session_id)
        if cached:
            cached.cached = True
            return cached

        started = time.monotonic()
        last_error: SessionGateError | None = None

        for attempt, delay_seconds in enumerate(self.backoff_seconds, start=1):
            if delay_seconds:
                self.sleep_fn(delay_seconds)
            try:
                details: dict[str, Any] = {}

                health_details = self.health_check() or {}
                details["health"] = health_details

                binding_details = self.bind_session(session_id) or {}
                details["binding"] = binding_details

                sentinel_details = self.sentinel_check() or {}
                sentinel_hits = int(sentinel_details.get("hits", 0))
                if sentinel_hits < 1:
                    raise SessionGateError(
                        classification=CLASS_TOOL_ROUTE_DOWN,
                        failure_stage="sentinel_query",
                        message="Sentinel query returned empty context",
                        details=sentinel_details,
                    )
                details["sentinel"] = sentinel_details

                result = SessionReadinessResult(
                    ready=True,
                    status="PASS",
                    session_id=session_id,
                    agent=agent,
                    transport=transport,
                    attempts=attempt,
                    sentinel_hits=sentinel_hits,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    details=details,
                )
                self._cache[session_id] = (time.monotonic(), result)
                return result
            except SessionGateError as exc:
                last_error = exc
                logger.warning(
                    "session_ready_retry attempt=%s/%s classification=%s stage=%s session=%s transport=%s agent=%s request_id=%s error=%s",
                    attempt,
                    len(self.backoff_seconds),
                    exc.classification,
                    exc.failure_stage,
                    session_id,
                    transport,
                    agent,
                    request_id or "-",
                    exc,
                )
            except Exception as exc:
                last_error = SessionGateError(
                    classification=CLASS_BACKEND_DOWN,
                    failure_stage="unexpected",
                    message=str(exc),
                    details={"exception_type": type(exc).__name__},
                )
                logger.warning(
                    "session_ready_retry attempt=%s/%s classification=%s stage=%s session=%s transport=%s agent=%s request_id=%s error=%s",
                    attempt,
                    len(self.backoff_seconds),
                    last_error.classification,
                    last_error.failure_stage,
                    session_id,
                    transport,
                    agent,
                    request_id or "-",
                    exc,
                )

        result = SessionReadinessResult(
            ready=False,
            status="NOT_READY",
            session_id=session_id,
            agent=agent,
            transport=transport,
            attempts=len(self.backoff_seconds),
            failure_stage=last_error.failure_stage if last_error else "unknown",
            classification=(
                last_error.classification if last_error else CLASS_BACKEND_DOWN
            ),
            error=str(last_error) if last_error else "Session readiness failed",
            latency_ms=int((time.monotonic() - started) * 1000),
            details=last_error.details if last_error else {},
        )
        self._log_incident(result)
        return result

    def _get_cached(self, session_id: str) -> SessionReadinessResult | None:
        cached = self._cache.get(session_id)
        if not cached:
            return None
        ts, result = cached
        if time.monotonic() - ts > self.ttl_seconds:
            self._cache.pop(session_id, None)
            return None
        return SessionReadinessResult(**result.to_dict())

    def _log_incident(self, result: SessionReadinessResult) -> None:
        logger.error(
            "session_ready_failed classification=%s stage=%s session=%s transport=%s agent=%s attempts=%s details=%s",
            result.classification,
            result.failure_stage,
            result.session_id,
            result.transport,
            result.agent,
            result.attempts,
            json.dumps(result.details, ensure_ascii=False, sort_keys=True),
        )
