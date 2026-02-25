"""Tests for agent_data.directus_sync module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_data.directus_sync import (
    _build_directus_payload,
    _enabled,
    _make_category,
    _make_slug,
    _make_summary,
    _should_sync,
    directus_sync_listener,
    handle_document_created,
    handle_document_deleted,
    handle_document_updated,
)


@pytest.mark.unit
class TestSlug:
    def test_basic(self):
        assert (
            _make_slug("knowledge/dev/blueprints/architecture-decisions.md")
            == "dev-blueprints-architecture-decisions"
        )

    def test_strip_docs_prefix(self):
        assert _make_slug("docs/current-state/overview.md") == "current-state-overview"

    def test_no_prefix(self):
        assert _make_slug("test/orphan-test") == "test-orphan-test"

    def test_underscores_and_spaces(self):
        assert _make_slug("knowledge/dev/my_document name.md") == "dev-my-document-name"


@pytest.mark.unit
class TestSummary:
    def test_first_paragraph(self):
        content = "# Title\n\nThis is the first paragraph.\n\nMore content."
        assert _make_summary(content) == "This is the first paragraph."

    def test_skip_headings_and_frontmatter(self):
        content = "---\nstatus: published\n---\n\n# Heading\n\nActual content here."
        assert _make_summary(content) == "Actual content here."

    def test_truncate_long(self):
        long = "A" * 300
        assert len(_make_summary(long)) == 200

    def test_empty(self):
        assert _make_summary("") == ""


@pytest.mark.unit
class TestCategory:
    def test_knowledge_prefix(self):
        assert _make_category("knowledge/dev/blueprints/file.md") == "dev"

    def test_no_knowledge_prefix(self):
        assert _make_category("operations/tasks/task-1") == "operations"

    def test_single_segment(self):
        assert _make_category("readme.md") == "readme.md"


@pytest.mark.unit
class TestBuildPayload:
    def test_create_has_version_group_id(self):
        doc_data = {
            "content": "# Hello\n\nWorld",
            "metadata": {"title": "Hello", "tags": ["a"], "status": "published"},
            "revision": 1,
        }
        payload = _build_directus_payload(
            "knowledge/dev/hello.md", doc_data, is_create=True
        )
        assert "version_group_id" in payload
        assert payload["title"] == "Hello"
        assert payload["slug"] == "dev-hello"
        assert payload["source_id"] == "agentdata:knowledge/dev/hello.md"
        assert payload["file_path"] == "knowledge/dev/hello.md"
        assert payload["status"] == "published"
        assert payload["category"] == "dev"
        assert payload["summary"] == "World"

    def test_update_no_version_group_id(self):
        doc_data = {
            "content": "Body text",
            "metadata": {"title": "T"},
            "revision": 3,
        }
        payload = _build_directus_payload("test/doc", doc_data, is_create=False)
        assert "version_group_id" not in payload
        assert payload["version_number"] == 3

    def test_invalid_status_defaults_to_published(self):
        doc_data = {
            "content": "",
            "metadata": {"title": "T", "status": "unknown"},
        }
        payload = _build_directus_payload("test/x", doc_data)
        assert payload["status"] == "published"

    def test_title_fallback(self):
        doc_data = {"content": "", "metadata": {}}
        payload = _build_directus_payload("knowledge/dev/my-doc.md", doc_data)
        assert payload["title"] == "my doc"


@pytest.mark.unit
class TestEnabled:
    def test_disabled_without_token(self):
        with patch("agent_data.directus_sync._DIRECTUS_TOKEN", ""):
            assert _enabled() is False

    def test_enabled_with_token(self):
        with patch("agent_data.directus_sync._DIRECTUS_TOKEN", "some-token"):
            assert _enabled() is True


@pytest.mark.unit
class TestSyncRouting:
    def test_knowledge_syncs(self):
        assert _should_sync("knowledge/dev/some-doc.md") is True
        assert _should_sync("knowledge/current-state/index.md") is True

    def test_operations_skips(self):
        assert _should_sync("operations/tasks/task-1") is False
        assert _should_sync("operations/tasks/comments/comment-1") is False

    def test_test_skips(self):
        assert _should_sync("test/some-test-doc") is False

    def test_root_skips(self):
        assert _should_sync("readme.md") is False

    def test_listener_skips_non_knowledge(self):
        """directus_sync_listener should not call handler for operations docs."""
        result = asyncio.run(
            directus_sync_listener(
                "document.created", {"document_id": "operations/tasks/task-99"}
            )
        )
        # Should return None (skipped) without calling any handler
        assert result is None


@pytest.mark.unit
class TestHandlers:
    def test_created_skipped_when_disabled(self):
        with patch("agent_data.directus_sync._DIRECTUS_TOKEN", ""):
            result = asyncio.run(handle_document_created({"document_id": "test/x"}))
            assert result["status"] == "skipped"

    def test_created_skipped_no_doc_id(self):
        with patch("agent_data.directus_sync._DIRECTUS_TOKEN", "tok"):
            result = asyncio.run(handle_document_created({}))
            assert result["status"] == "skipped"

    def test_updated_skipped_when_disabled(self):
        with patch("agent_data.directus_sync._DIRECTUS_TOKEN", ""):
            result = asyncio.run(handle_document_updated({"document_id": "test/x"}))
            assert result["status"] == "skipped"

    def test_deleted_skipped_when_disabled(self):
        with patch("agent_data.directus_sync._DIRECTUS_TOKEN", ""):
            result = asyncio.run(handle_document_deleted({"document_id": "test/x"}))
            assert result["status"] == "skipped"

    def test_created_error_when_fetch_fails(self):
        with (
            patch("agent_data.directus_sync._DIRECTUS_TOKEN", "tok"),
            patch(
                "agent_data.directus_sync._fetch_document", new_callable=AsyncMock
            ) as mock_fetch,
        ):
            mock_fetch.return_value = None
            result = asyncio.run(handle_document_created({"document_id": "test/x"}))
            assert result["status"] == "error"
            assert "could not fetch" in result["reason"]

    def test_created_success_new_doc(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"id": 999}}

        mock_client = AsyncMock()
        mock_client.get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"data": []})
        )
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("agent_data.directus_sync._DIRECTUS_TOKEN", "tok"),
            patch(
                "agent_data.directus_sync._fetch_document",
                new_callable=AsyncMock,
                return_value={
                    "content": "hello",
                    "metadata": {"title": "T"},
                    "revision": 1,
                },
            ),
            patch(
                "agent_data.directus_sync.httpx.AsyncClient", return_value=mock_client
            ),
        ):
            result = asyncio.run(
                handle_document_created({"document_id": "test/new-doc"})
            )
            assert result["status"] == "created"
            assert result["directus_id"] == 999

    def test_deleted_not_found(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"data": []})
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("agent_data.directus_sync._DIRECTUS_TOKEN", "tok"),
            patch(
                "agent_data.directus_sync.httpx.AsyncClient", return_value=mock_client
            ),
        ):
            result = asyncio.run(handle_document_deleted({"document_id": "test/gone"}))
            assert result["status"] == "not_found"

    def test_deleted_success(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": 42,
                            "title": "X",
                            "source_id": "agentdata:test/x",
                            "file_path": "test/x",
                        }
                    ]
                }
            ),
        )
        mock_client.delete.return_value = MagicMock(status_code=204)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("agent_data.directus_sync._DIRECTUS_TOKEN", "tok"),
            patch(
                "agent_data.directus_sync.httpx.AsyncClient", return_value=mock_client
            ),
        ):
            result = asyncio.run(handle_document_deleted({"document_id": "test/x"}))
            assert result["status"] == "deleted"
            assert result["directus_id"] == 42
