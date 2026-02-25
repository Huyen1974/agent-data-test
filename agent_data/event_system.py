"""Event System — Webhook on Write for Agent Data (WEB-82, TD-001).

Fires HTTP POST webhooks to subscribers after every successful CRUD
operation on documents. Async fire-and-forget — never blocks the
CRUD response.

Components:
  EventBus     — emit(event_type, payload) after CRUD success
  WebhookMgr   — dispatch HTTP POST to subscribers with retry
  Registry     — config-based subscriber list (JSON file or env)
  EventLog     — in-memory audit trail with rotation
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------
DOCUMENT_CREATED = "document.created"
DOCUMENT_UPDATED = "document.updated"
DOCUMENT_DELETED = "document.deleted"

ALL_EVENT_TYPES = {DOCUMENT_CREATED, DOCUMENT_UPDATED, DOCUMENT_DELETED}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class WebhookConfig:
    id: str
    url: str
    events: list[str]
    headers: dict[str, str] = field(default_factory=dict)
    active: bool = True
    retry_policy: dict[str, Any] = field(
        default_factory=lambda: {"max_retries": 3, "backoff": [5, 30, 300]}
    )


@dataclass
class EventRecord:
    event_type: str
    document_id: str
    timestamp: str
    payload: dict[str, Any]
    webhook_results: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WebhookHealth:
    total_calls: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_success: str | None = None
    last_failure: str | None = None
    last_error: str | None = None


# ---------------------------------------------------------------------------
# EventLog — in-memory audit trail with rotation
# ---------------------------------------------------------------------------
class EventLog:
    """Bounded event log: keeps last N entries or 7-day window."""

    def __init__(self, max_entries: int = 10000) -> None:
        self._entries: deque[EventRecord] = deque(maxlen=max_entries)

    def record(self, entry: EventRecord) -> None:
        self._entries.append(entry)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        items = list(self._entries)[-limit:]
        items.reverse()
        return [
            {
                "event_type": e.event_type,
                "document_id": e.document_id,
                "timestamp": e.timestamp,
                "webhook_results": e.webhook_results,
            }
            for e in items
        ]

    def count(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# WebhookRegistry — load subscribers from config
# ---------------------------------------------------------------------------
class WebhookRegistry:
    """Manages webhook subscriber configurations."""

    def __init__(self) -> None:
        self._webhooks: dict[str, WebhookConfig] = {}

    def load_from_dict(self, data: dict[str, Any]) -> int:
        """Load webhooks from a dict (parsed JSON config)."""
        loaded = 0
        for wh in data.get("webhooks", []):
            wid = wh.get("id", "")
            if not wid or not wh.get("url"):
                continue
            headers = wh.get("headers", {})
            resolved_headers = {}
            for k, v in headers.items():
                resolved_headers[k] = _resolve_env(v)
            self._webhooks[wid] = WebhookConfig(
                id=wid,
                url=wh["url"],
                events=wh.get("events", list(ALL_EVENT_TYPES)),
                headers=resolved_headers,
                active=wh.get("active", True),
                retry_policy=wh.get(
                    "retry_policy",
                    {"max_retries": 3, "backoff": [5, 30, 300]},
                ),
            )
            loaded += 1
        return loaded

    def load_from_file(self, path: str) -> int:
        """Load webhooks from a JSON config file."""
        try:
            with open(path) as f:
                data = json.load(f)
            return self.load_from_dict(data)
        except FileNotFoundError:
            logger.info("Webhook config file not found: %s", path)
            return 0
        except Exception as exc:
            logger.error("Failed to load webhook config %s: %s", path, exc)
            return 0

    def add(self, config: WebhookConfig) -> None:
        self._webhooks[config.id] = config

    def remove(self, webhook_id: str) -> bool:
        return self._webhooks.pop(webhook_id, None) is not None

    def get(self, webhook_id: str) -> WebhookConfig | None:
        return self._webhooks.get(webhook_id)

    def list_all(self) -> list[WebhookConfig]:
        return list(self._webhooks.values())

    def subscribers_for(self, event_type: str) -> list[WebhookConfig]:
        return [
            wh
            for wh in self._webhooks.values()
            if wh.active and event_type in wh.events
        ]


def _resolve_env(value: str) -> str:
    """Resolve ${ENV_VAR} placeholders in header values."""
    if not isinstance(value, str):
        return value
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.getenv(env_name, "")
    return value


# ---------------------------------------------------------------------------
# WebhookManager — dispatch HTTP POST with retry
# ---------------------------------------------------------------------------
class WebhookManager:
    """Dispatches webhook HTTP POST calls with retry and health tracking."""

    def __init__(self, registry: WebhookRegistry, event_log: EventLog) -> None:
        self.registry = registry
        self.event_log = event_log
        self._health: dict[str, WebhookHealth] = {}

    async def dispatch(
        self, event_type: str, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Dispatch event to all matching subscribers. Returns results list."""
        subscribers = self.registry.subscribers_for(event_type)
        if not subscribers:
            return []

        results = []
        tasks = [self._call_webhook(wh, event_type, payload) for wh in subscribers]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        for wh, outcome in zip(subscribers, outcomes, strict=False):
            if isinstance(outcome, Exception):
                result = {
                    "webhook_id": wh.id,
                    "status": "error",
                    "error": str(outcome),
                }
            else:
                result = outcome
            results.append(result)
        return results

    async def _call_webhook(
        self,
        wh: WebhookConfig,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a single webhook with retry."""
        backoff = wh.retry_policy.get("backoff", [5, 30, 300])
        max_retries = wh.retry_policy.get("max_retries", 3)
        health = self._get_health(wh.id)

        body = {"event_type": event_type, "payload": payload}
        last_error = ""

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        wh.url,
                        json=body,
                        headers=wh.headers,
                    )
                health.total_calls += 1
                if resp.status_code < 400:
                    health.success_count += 1
                    health.last_success = datetime.now(UTC).isoformat()
                    return {
                        "webhook_id": wh.id,
                        "status": "delivered",
                        "http_status": resp.status_code,
                        "attempt": attempt + 1,
                    }
                last_error = f"HTTP {resp.status_code}"
                health.fail_count += 1
                health.last_failure = datetime.now(UTC).isoformat()
                health.last_error = last_error
            except Exception as exc:
                last_error = str(exc)
                health.total_calls += 1
                health.fail_count += 1
                health.last_failure = datetime.now(UTC).isoformat()
                health.last_error = last_error

            if attempt < max_retries:
                delay = backoff[min(attempt, len(backoff) - 1)]
                logger.warning(
                    "Webhook %s attempt %d failed (%s), retry in %ds",
                    wh.id,
                    attempt + 1,
                    last_error,
                    delay,
                )
                await asyncio.sleep(delay)

        logger.error(
            "Webhook %s exhausted retries (%d): %s",
            wh.id,
            max_retries + 1,
            last_error,
        )
        return {
            "webhook_id": wh.id,
            "status": "failed",
            "error": last_error,
            "attempts": max_retries + 1,
        }

    def _get_health(self, webhook_id: str) -> WebhookHealth:
        if webhook_id not in self._health:
            self._health[webhook_id] = WebhookHealth()
        return self._health[webhook_id]

    def get_health(self, webhook_id: str) -> dict[str, Any]:
        h = self._get_health(webhook_id)
        rate = (
            round(h.success_count / h.total_calls * 100, 1) if h.total_calls > 0 else 0
        )
        return {
            "webhook_id": webhook_id,
            "total_calls": h.total_calls,
            "success_count": h.success_count,
            "fail_count": h.fail_count,
            "success_rate": rate,
            "last_success": h.last_success,
            "last_failure": h.last_failure,
            "last_error": h.last_error,
        }

    async def test_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Send a test event to a specific webhook."""
        wh = self.registry.get(webhook_id)
        if not wh:
            return {"error": f"Webhook {webhook_id} not found"}
        test_payload = {
            "document_id": "__test__",
            "path": "__test__",
            "title": "Test Event",
            "timestamp": datetime.now(UTC).isoformat(),
            "changes_summary": "Test webhook delivery",
        }
        return await self._call_webhook(wh, "document.test", test_payload)


# ---------------------------------------------------------------------------
# EventBus — main interface for emitting events
# ---------------------------------------------------------------------------
class EventBus:
    """Central event bus: emit events after CRUD, dispatch to webhooks."""

    def __init__(
        self,
        webhook_manager: WebhookManager,
        event_log: EventLog,
    ) -> None:
        self.webhook_manager = webhook_manager
        self.event_log = event_log
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit an event. Fire-and-forget — errors are logged, never raised."""
        if not self._enabled:
            return
        if event_type not in ALL_EVENT_TYPES:
            logger.warning("Unknown event type: %s", event_type)
            return

        timestamp = datetime.now(UTC).isoformat()
        payload["timestamp"] = timestamp
        doc_id = payload.get("document_id", "unknown")

        logger.info(
            "event_emitted",
            extra={
                "event_type": event_type,
                "document_id": doc_id,
            },
        )

        record = EventRecord(
            event_type=event_type,
            document_id=doc_id,
            timestamp=timestamp,
            payload=payload,
        )

        try:
            results = await self.webhook_manager.dispatch(event_type, payload)
            record.webhook_results = results
        except Exception as exc:
            logger.error("Webhook dispatch failed: %s", exc)
            record.webhook_results = [{"status": "error", "error": str(exc)}]

        self.event_log.record(record)

    def emit_fire_and_forget(self, event_type: str, payload: dict[str, Any]) -> None:
        """Schedule emit() as a background task. Never blocks caller."""
        if not self._enabled:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._safe_emit(event_type, payload))
        except RuntimeError:
            logger.warning("No event loop for fire-and-forget emit")

    async def _safe_emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Wrapper that catches all exceptions to prevent task crashes."""
        try:
            await self.emit(event_type, payload)
        except Exception as exc:
            logger.error("Event emit failed (swallowed): %s", exc)

    def status(self) -> dict[str, Any]:
        """Return event system status for health checks."""
        webhooks = self.webhook_manager.registry.list_all()
        return {
            "enabled": self._enabled,
            "webhooks_registered": len(webhooks),
            "webhooks_active": sum(1 for w in webhooks if w.active),
            "events_logged": self.event_log.count(),
        }


# ---------------------------------------------------------------------------
# Factory — build the full event system
# ---------------------------------------------------------------------------
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the singleton EventBus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = _build_event_bus()
    return _event_bus


def _build_event_bus() -> EventBus:
    """Build EventBus with registry loaded from config."""
    event_log = EventLog(max_entries=10000)
    registry = WebhookRegistry()

    # Load from config file (if exists)
    config_path = os.getenv(
        "WEBHOOK_CONFIG",
        os.path.join(os.path.dirname(__file__), "..", "webhook_config.json"),
    )
    config_path = os.path.normpath(config_path)
    loaded = registry.load_from_file(config_path)
    if loaded:
        logger.info("Loaded %d webhook(s) from %s", loaded, config_path)

    # Load from environment variable (JSON string)
    env_config = os.getenv("WEBHOOK_CONFIG_JSON", "").strip()
    if env_config:
        try:
            data = json.loads(env_config)
            env_loaded = registry.load_from_dict(data)
            logger.info("Loaded %d webhook(s) from WEBHOOK_CONFIG_JSON", env_loaded)
        except json.JSONDecodeError as exc:
            logger.error("Invalid WEBHOOK_CONFIG_JSON: %s", exc)

    webhook_mgr = WebhookManager(registry, event_log)
    bus = EventBus(webhook_mgr, event_log)
    logger.info("Event system initialized: %d webhooks", len(registry.list_all()))
    return bus
