from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions

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

    Ensures that the AgentData instance exposes the tool name in a tools
    collection for simple discovery, and that calling the tool method returns
    the expected placeholder message containing the input URI.
    """

    cfg = AgentDataConfig()
    cfg.vecdb = None

    agent = AgentData(cfg)

    # Verify tool registration list contains our tool
    assert hasattr(agent, "tools"), "Agent should expose a tools collection"
    assert "gcs_ingest" in agent.tools

    # Verify placeholder logic returns the URI
    uri = "gs://fake-bucket/test.pdf"
    result = agent.gcs_ingest(uri)
    assert uri in result


@pytest.mark.unit
@patch("agent_data.main.storage")
def test_gcs_ingest_download_success(
    mock_storage: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """Mock a successful GCS download via storage.Client and ensure it's called."""
    # Arrange: mock storage client, bucket, and blob
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    # To align with the corrected implementation, we now simulate the side-effect
    # of `ingest_doc_paths`, which is to populate `doc_segments`.
    from langroid.mytypes import Document

    expected_text = "Framework text"

    def mock_ingest(paths, *args, **kwargs):
        agent.doc_segments = [
            Document(content=expected_text, metadata={"source": paths[0]})
        ]
        return "Mock ingestion result."

    monkeypatch.setattr(agent, "ingest_doc_paths", mock_ingest)

    uri = "gs://test-bucket/test.txt"
    result = agent.gcs_ingest(uri)

    # Ensure download and ingestion were invoked
    mock_blob.download_to_filename.assert_called_once()
    # Check that our mock was called.
    # We can no longer use a patch here because we replaced the method on the instance.
    # A simple check of the result is sufficient.
    assert "Mock ingestion result." in result
    # last_ingested_text should be set from the content in our mocked doc_segments
    assert agent.last_ingested_text == expected_text


@pytest.mark.unit
@patch("agent_data.main.storage")
def test_gcs_ingest_handles_not_found_error(mock_storage: MagicMock):
    """Ensure NotFound errors are translated into a friendly message."""

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_storage.Client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    # Configure the blob to raise NotFound from google.api_core.exceptions
    mock_blob.download_to_filename.side_effect = exceptions.NotFound("not found")

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    uri = "gs://test-bucket/missing.txt"
    result = agent.gcs_ingest(uri)

    assert "File not found" in result


@pytest.mark.unit
def test_gcs_ingest_missing_client_libraries(monkeypatch: pytest.MonkeyPatch):
    """When GCS client libs are unavailable, method returns helpful message."""

    import agent_data.main as adm

    # Simulate unavailable google-cloud libraries
    monkeypatch.setattr(adm, "storage", None, raising=False)
    monkeypatch.setattr(adm, "exceptions", None, raising=False)

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.gcs_ingest("gs://bucket/obj.txt")
    assert "GCS client libraries not available" in res


@pytest.mark.unit
@patch("agent_data.main.storage")
def test_gcs_ingest_handles_forbidden_error(mock_storage: MagicMock):
    """Ensure Forbidden errors produce an access message."""

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_blob.download_to_filename.side_effect = exceptions.Forbidden("forbidden")

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.gcs_ingest("gs://bucket/protected.txt")
    assert "Access forbidden" in res


@pytest.mark.unit
def test_gcs_ingest_invalid_uri_returns_failure_message():
    """Invalid URI should be handled and return a failure message."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.gcs_ingest("http://not-a-gcs-uri")
    assert "Failed to download" in res


@pytest.mark.unit
@patch("agent_data.main.FirestoreChatHistory")
def test_agent_data_initializes_firestore_history(mock_fsh):
    """AgentData should initialize FirestoreChatHistory and assign to history.

    Verifies the integration point by asserting the class is instantiated
    once and the resulting instance is assigned to agent.history.
    """

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    mock_fsh.assert_called_once()
    assert agent.history is mock_fsh.return_value


@pytest.mark.unit
def test_gcs_ingest_invalid_uri_missing_object_path():
    """URI missing object path should be handled with failure message."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.gcs_ingest("gs://bucket-only")
    assert "Failed to download" in res


@pytest.mark.unit
def test_gcs_ingest_invalid_uri_empty_blob():
    """URI with empty blob path should be handled with failure message."""

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.gcs_ingest("gs://bucket/")
    assert "Failed to download" in res


# ==== Firestore tool skeleton tests ====


@pytest.mark.unit
@patch("agent_data.main.firestore")
def test_add_metadata_tool_calls_firestore(mock_firestore: MagicMock):
    """Ensure add_metadata parses JSON and calls Firestore .set with dict."""

    # Arrange Firestore mock chain
    client = mock_firestore.Client.return_value
    coll = client.collection.return_value
    doc_ref = coll.document.return_value

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    # Act
    result = agent.add_metadata(document_id="doc1", metadata_json='{"data":"test"}')

    # Assert
    assert "saved" in result
    doc_ref.set.assert_called_once_with({"data": "test"})


@pytest.mark.unit
@patch("agent_data.main.firestore")
def test_get_metadata_tool_returns_json(mock_firestore: MagicMock):
    """Ensure get_metadata returns JSON from Firestore doc."""

    client = mock_firestore.Client.return_value
    coll = client.collection.return_value
    doc_ref = coll.document.return_value
    # Mock a document snapshot
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {"data": "mock_value"}
    doc_ref.get.return_value = doc

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.get_metadata("doc1")
    assert out == '{"data": "mock_value"}' or out == '{"data":"mock_value"}'


@pytest.mark.unit
@patch("agent_data.main.firestore")
def test_get_metadata_tool_not_found(mock_firestore: MagicMock):
    """Ensure get_metadata returns not-found when doc does not exist."""

    client = mock_firestore.Client.return_value
    coll = client.collection.return_value
    doc_ref = coll.document.return_value
    doc = MagicMock()
    doc.exists = False
    doc_ref.get.return_value = doc

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.get_metadata("doc1")
    assert "Metadata not found" in out


@pytest.mark.unit
@patch("agent_data.main.firestore")
def test_update_status_tool_calls_firestore(mock_firestore: MagicMock):
    """Ensure update_ingestion_status calls Firestore .update with correct dict."""

    client = mock_firestore.Client.return_value
    coll = client.collection.return_value
    doc_ref = coll.document.return_value

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    out = agent.update_ingestion_status(document_id="doc1", status="completed")
    assert "updated to 'completed'" in out
    doc_ref.update.assert_called_once_with({"ingestion_status": "completed"})


@pytest.mark.unit
@patch("agent_data.main.firestore")
@patch("agent_data.main.AgentData.add_metadata")
@patch("langroid.agent.special.doc_chat_agent.DocChatAgent.ingest_doc_paths")
def test_ingest_doc_paths_override_saves_metadata(
    mock_super_ingest: MagicMock,
    mock_add_metadata: MagicMock,
    mock_firestore: MagicMock,
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
@patch("agent_data.main.storage")
def test_gcs_ingest_handles_api_error(mock_storage: MagicMock):
    """Simulate a generic Google API error during download."""

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_storage.Client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_blob.download_to_filename.side_effect = exceptions.GoogleAPICallError("boom")

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    res = agent.gcs_ingest("gs://bucket/file.txt")
    assert "GCS API error" in res


@pytest.mark.unit
@patch("agent_data.main.storage")
def test_gcs_ingest_binary_file_caches_extracted_text(
    mock_storage: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """Ensure gcs_ingest caches extracted text from doc_segments for binary files."""
    # Arrange: mock GCS client to "download" a fake binary file
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    # Simulate downloading a binary file by writing bytes to the mock path
    def fake_download(path):
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\n%%EOF")

    mock_blob.download_to_filename.side_effect = fake_download

    cfg = AgentDataConfig()
    cfg.vecdb = None
    agent = AgentData(cfg)

    # This is the expected text after a real parser would have run
    expected_text = "This is the extracted text from a binary file."

    # Mock the parent ingestion to simulate its behavior: populating doc_segments
    # instead of doing a full ingestion.
    from langroid.mytypes import Document

    def mock_ingest(paths, *args, **kwargs):
        agent.doc_segments = [
            Document(content=expected_text, metadata={"source": paths[0]})
        ]
        return "Mock ingestion complete."

    monkeypatch.setattr(agent, "ingest_doc_paths", mock_ingest)

    uri = "gs://test-bucket/document.pdf"
    agent.gcs_ingest(uri)

    # Assert that the cached text is the clean, extracted content, not the raw bytes
    assert agent.last_ingested_text == expected_text
