"""Tests for agent_data.event_system module."""

from __future__ import annotations

import pytest

from agent_data.event_system import (
    DOCUMENT_CREATED,
    DOCUMENT_DELETED,
    DOCUMENT_UPDATED,
    EventBus,
    EventLog,
    WebhookConfig,
    WebhookManager,
    WebhookRegistry,
)


@pytest.mark.unit
class TestEventLog:
    def test_record_and_recent(self):
        log = EventLog(max_entries=100)
        assert log.count() == 0

        from agent_data.event_system import EventRecord

        record = EventRecord(
            event_type=DOCUMENT_CREATED,
            document_id="doc-1",
            timestamp="2026-01-01T00:00:00",
            payload={"document_id": "doc-1"},
        )
        log.record(record)
        assert log.count() == 1

        recent = log.recent(10)
        assert len(recent) == 1
        assert recent[0]["document_id"] == "doc-1"
        assert recent[0]["event_type"] == DOCUMENT_CREATED

    def test_max_entries_rotation(self):
        log = EventLog(max_entries=3)
        from agent_data.event_system import EventRecord

        for i in range(5):
            log.record(
                EventRecord(
                    event_type=DOCUMENT_CREATED,
                    document_id=f"doc-{i}",
                    timestamp=f"2026-01-01T00:0{i}:00",
                    payload={"document_id": f"doc-{i}"},
                )
            )
        assert log.count() == 3
        recent = log.recent(10)
        assert recent[0]["document_id"] == "doc-4"


@pytest.mark.unit
class TestWebhookRegistry:
    def test_load_from_dict(self):
        registry = WebhookRegistry()
        data = {
            "webhooks": [
                {
                    "id": "test-hook",
                    "url": "https://example.com/webhook",
                    "events": [DOCUMENT_CREATED],
                    "active": True,
                }
            ]
        }
        loaded = registry.load_from_dict(data)
        assert loaded == 1
        assert len(registry.list_all()) == 1

    def test_subscribers_for(self):
        registry = WebhookRegistry()
        registry.add(
            WebhookConfig(
                id="hook-1",
                url="https://example.com/hook1",
                events=[DOCUMENT_CREATED, DOCUMENT_UPDATED],
                active=True,
            )
        )
        registry.add(
            WebhookConfig(
                id="hook-2",
                url="https://example.com/hook2",
                events=[DOCUMENT_DELETED],
                active=True,
            )
        )
        registry.add(
            WebhookConfig(
                id="hook-3",
                url="https://example.com/hook3",
                events=[DOCUMENT_CREATED],
                active=False,
            )
        )

        subs = registry.subscribers_for(DOCUMENT_CREATED)
        assert len(subs) == 1
        assert subs[0].id == "hook-1"

        subs = registry.subscribers_for(DOCUMENT_DELETED)
        assert len(subs) == 1
        assert subs[0].id == "hook-2"

    def test_remove(self):
        registry = WebhookRegistry()
        registry.add(
            WebhookConfig(id="x", url="https://x.com", events=[DOCUMENT_CREATED])
        )
        assert registry.remove("x") is True
        assert registry.remove("x") is False
        assert len(registry.list_all()) == 0

    def test_env_resolution(self):
        import os

        os.environ["TEST_TOKEN_ABC"] = "my-secret"
        registry = WebhookRegistry()
        data = {
            "webhooks": [
                {
                    "id": "env-test",
                    "url": "https://example.com",
                    "headers": {"Authorization": "${TEST_TOKEN_ABC}"},
                }
            ]
        }
        registry.load_from_dict(data)
        wh = registry.get("env-test")
        assert wh is not None
        assert wh.headers["Authorization"] == "my-secret"
        del os.environ["TEST_TOKEN_ABC"]


@pytest.mark.unit
class TestEventBus:
    def test_emit_disabled(self):
        log = EventLog()
        registry = WebhookRegistry()
        mgr = WebhookManager(registry, log)
        bus = EventBus(mgr, log)
        bus.enabled = False

        bus.emit_fire_and_forget(DOCUMENT_CREATED, {"document_id": "d1"})
        assert log.count() == 0

    def test_emit_records_event(self):
        import asyncio

        log = EventLog()
        registry = WebhookRegistry()
        mgr = WebhookManager(registry, log)
        bus = EventBus(mgr, log)

        asyncio.run(bus.emit(DOCUMENT_CREATED, {"document_id": "doc-1", "title": "T"}))
        assert log.count() == 1
        recent = log.recent(1)
        assert recent[0]["event_type"] == DOCUMENT_CREATED
        assert recent[0]["document_id"] == "doc-1"

    def test_status(self):
        log = EventLog()
        registry = WebhookRegistry()
        registry.add(
            WebhookConfig(
                id="a", url="https://a.com", events=[DOCUMENT_CREATED], active=True
            )
        )
        registry.add(
            WebhookConfig(
                id="b", url="https://b.com", events=[DOCUMENT_CREATED], active=False
            )
        )
        mgr = WebhookManager(registry, log)
        bus = EventBus(mgr, log)

        status = bus.status()
        assert status["enabled"] is True
        assert status["webhooks_registered"] == 2
        assert status["webhooks_active"] == 1
        assert status["events_logged"] == 0
