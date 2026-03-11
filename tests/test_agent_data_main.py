from unittest.mock import MagicMock, patch

import pytest

from agent_data.main import AgentData, AgentDataConfig


@pytest.mark.unit
def test_agent_data_instantiation():
    """Basic instantiation test for AgentData core class.

    Ensures that an AgentData instance can be created from a default
    AgentDataConfig, and the resulting object is an instance of AgentData.
    """

    cfg = AgentDataConfig()
    # Avoid external dependencies during unit test
    # by disabling vector store initialization
    cfg.vecdb = None
    agent = AgentData(cfg)
    assert isinstance(agent, AgentData)


@pytest.mark.unit
def test_agent_data_config_handling():
    """Ensure AgentData preserves provided config attributes.

    We mock key config attributes to avoid external dependencies and
    verify they are retained on the instantiated AgentData.
    """

    cfg = AgentDataConfig()
    # Avoid external services in unit tests
    cfg.vecdb = None
    cfg.llm = None

    agent = AgentData(cfg)

    assert agent.config is cfg
    assert getattr(agent.config, "vecdb", "__missing__") is None
    assert getattr(agent.config, "llm", "__missing__") is None


@pytest.mark.unit
def test_gcs_ingest_is_registered_tool():
    """Verify the gcs_ingest tool is registered and callable.

    Since S109, gcs_ingest returns a disabled message for all URIs.
    """

    cfg = AgentDataConfig()
    cfg.vecdb = None

    agent = AgentData(cfg)

    # Verify tool registration list contains our tool
    assert hasattr(agent, "tools"), "Agent should expose a tools collection"
    assert "gcs_ingest" in agent.tools

    # Verify disabled message returns the URI
    uri = "gs://fake-bucket/test.pdf"
    result = agent.gcs_ingest(uri)
    assert uri in result
    assert "disabled" in result.lower()


@pytest.mark.unit
def test_gcs_ingest_returns_disabled_message():
    """After S109 migration, gcs_ingest always returns disabled message."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    result = agent.gcs_ingest("gs://test-bucket/test.txt")
    assert "disabled" in result.lower()
    assert "inline text ingestion" in result.lower()


@pytest.mark.unit
def test_gcs_ingest_disabled_for_any_uri():
    """gcs_ingest returns disabled message regardless of URI format."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    for uri in [
        "gs://bucket/file.txt",
        "http://not-a-gcs-uri",
        "gs://bucket-only",
        "gs://bucket/",
    ]:
        res = agent.gcs_ingest(uri)
        assert "disabled" in res.lower(), f"Expected disabled message for {uri}"


@pytest.mark.unit
@patch("agent_data.main.PostgresChatHistory")
def test_agent_data_initializes_chat_history(mock_pch):
    """AgentData should initialize PostgresChatHistory and assign to history."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    mock_pch.assert_called_once()
    assert agent.history is mock_pch.return_value


# ==== PostgreSQL metadata tool tests ====


@pytest.mark.unit
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_add_metadata_tool_calls_pg_store(
    mock_ensure: MagicMock,
    mock_init: MagicMock,
    mock_set_doc: MagicMock,
):
    """Ensure add_metadata parses JSON and calls pg_store.set_doc."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    result = agent.add_metadata(document_id="doc1", metadata_json='{"data":"test"}')

    assert "saved" in result
    mock_set_doc.assert_called_once_with("metadata_store", "doc1", {"data": "test"})


@pytest.mark.unit
@patch("agent_data.pg_store.get_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_get_metadata_tool_returns_json(
    mock_ensure: MagicMock,
    mock_init: MagicMock,
    mock_get_doc: MagicMock,
):
    """Ensure get_metadata returns JSON from pg_store."""

    mock_get_doc.return_value = {"data": "mock_value"}

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.get_metadata("doc1")
    assert out == '{"data": "mock_value"}' or out == '{"data":"mock_value"}'
    mock_get_doc.assert_called_once_with("metadata_store", "doc1")


@pytest.mark.unit
@patch("agent_data.pg_store.get_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_get_metadata_tool_not_found(
    mock_ensure: MagicMock,
    mock_init: MagicMock,
    mock_get_doc: MagicMock,
):
    """Ensure get_metadata returns not-found when doc does not exist."""

    mock_get_doc.return_value = None

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.get_metadata("doc1")
    assert "Metadata not found" in out


@pytest.mark.unit
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_update_status_tool_calls_pg_store(
    mock_ensure: MagicMock,
    mock_init: MagicMock,
    mock_update_doc: MagicMock,
):
    """Ensure update_ingestion_status calls pg_store.update_doc."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.update_ingestion_status(document_id="doc1", status="completed")
    assert "updated to 'completed'" in out
    mock_update_doc.assert_called_once_with(
        "metadata_store", "doc1", {"ingestion_status": "completed"}
    )


@pytest.mark.unit
@patch("agent_data.main.AgentData.add_metadata")
@patch("langroid.agent.special.doc_chat_agent.DocChatAgent.ingest_doc_paths")
@patch("agent_data.pg_store.init_pool")
@patch("agent_data.pg_store.ensure_tables")
def test_ingest_doc_paths_override_saves_metadata(
    mock_ensure: MagicMock,
    mock_init: MagicMock,
    mock_super_ingest: MagicMock,
    mock_add_metadata: MagicMock,
):
    """Override calls parent ingest and persists metadata per path (skip bytes)."""

    mock_super_ingest.return_value = "OK"
    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    paths = ["/path/to/doc1.txt", "/path/to/doc2.pdf", b"bytes-content"]
    out = agent.ingest_doc_paths(paths=paths)

    # Parent called once with the same positional paths list
    mock_super_ingest.assert_called_once()
    called_args, called_kwargs = mock_super_ingest.call_args
    assert called_args[0] == paths

    # add_metadata called for two string paths only
    assert mock_add_metadata.call_count == 2
    assert "Ingestion complete." in out


@pytest.mark.unit
def test_add_metadata_no_db():
    """When PostgreSQL is not initialized, add_metadata returns error message."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)
    agent.db = None

    result = agent.add_metadata(document_id="doc1", metadata_json='{"data":"test"}')
    assert "not initialized" in result.lower()
