"""PostgreSQL metadata integration tests (migrated from Firestore).

These tests verify that AgentData metadata tools correctly interact
with the pg_store module after the S109 migration.
"""

from unittest.mock import MagicMock, patch

import pytest

from agent_data.main import AgentData, AgentDataConfig


@pytest.mark.unit
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_add_metadata_success(
    mock_ensure: MagicMock, mock_init: MagicMock, mock_set_doc: MagicMock
):
    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.add_metadata("doc1", '{"k": "v"}')
    assert "saved" in out
    mock_set_doc.assert_called_once_with("metadata_store", "doc1", {"k": "v"})


@pytest.mark.unit
@patch("agent_data.pg_store.get_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_get_metadata_found(
    mock_ensure: MagicMock, mock_init: MagicMock, mock_get_doc: MagicMock
):
    mock_get_doc.return_value = {"data": "mock"}

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.get_metadata("docX")
    assert res == '{"data": "mock"}' or res == '{"data":"mock"}'
    mock_get_doc.assert_called_once_with("metadata_store", "docX")


@pytest.mark.unit
@patch("agent_data.pg_store.get_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_get_metadata_not_found(
    mock_ensure: MagicMock, mock_init: MagicMock, mock_get_doc: MagicMock
):
    mock_get_doc.return_value = None

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.get_metadata("docY")
    assert "not found" in res.lower()


@pytest.mark.unit
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_update_status_success(
    mock_ensure: MagicMock, mock_init: MagicMock, mock_update_doc: MagicMock
):
    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.update_ingestion_status("docZ", "completed")
    assert "updated" in res and "completed" in res
    mock_update_doc.assert_called_once_with(
        "metadata_store", "docZ", {"ingestion_status": "completed"}
    )


@pytest.mark.unit
@patch("agent_data.main.AgentData.add_metadata")
@patch("langroid.agent.special.doc_chat_agent.DocChatAgent.ingest_doc_paths")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_ingest_override_calls_add_metadata(
    mock_ensure: MagicMock,
    mock_init: MagicMock,
    mock_super_ingest: MagicMock,
    mock_add_metadata: MagicMock,
):
    mock_super_ingest.return_value = "OK"
    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    paths = ["/tmp/a.txt", "/tmp/b.pdf"]
    msg = agent.ingest_doc_paths(paths)
    mock_super_ingest.assert_called_once()
    assert mock_add_metadata.call_count == len(paths)
    assert "Ingestion complete." in msg
