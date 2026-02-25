"""Tests for agent_data.directus_sync module."""

from __future__ import annotations

import pytest

from agent_data.directus_sync import _make_category, _make_slug, _make_summary


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
