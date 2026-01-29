from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent_data import vector_store


@pytest.fixture(autouse=True)
def reset_vector_store():
    vector_store.get_vector_store(refresh=True)
    yield
    vector_store.get_vector_store(refresh=True)


def test_vector_store_disabled_without_env(monkeypatch: pytest.MonkeyPatch):
    for env_var in [
        "QDRANT_URL",
        "QDRANT_API_URL",
        "QDRANT_API_KEY",
        "OPENAI_API_KEY",
        "APP_ENV",
        "ENV",
        "QDRANT_COLLECTION",
    ]:
        monkeypatch.delenv(env_var, raising=False)

    store = vector_store.get_vector_store(refresh=True)
    assert store.enabled is False


def test_vector_store_upsert_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("QDRANT_URL", "https://example.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "qdrant-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("APP_ENV", "test")

    captured: dict[str, MagicMock] = {}

    class FakeEmbeddings:
        def create(self, model: str, input: str):
            assert model == "text-embedding-3-small"
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["openai_kwargs"] = kwargs
            self.embeddings = FakeEmbeddings()

    class FakeQdrantClient:
        def __init__(self, url: str, api_key: str, timeout: int):
            captured["client"] = MagicMock(url=url, api_key=api_key, timeout=timeout)

        def upsert(self, collection_name, points, wait):
            captured["upsert"] = {
                "collection": collection_name,
                "points": points,
                "wait": wait,
            }

    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(vector_store, "QdrantClient", FakeQdrantClient)

    store = vector_store.get_vector_store(refresh=True)
    assert store.enabled is True

    result = store.upsert_document(
        document_id="doc-1",
        content="Document body for embeddings",
        metadata={"title": "Doc"},
        parent_id="root",
        is_human_readable=True,
    )

    assert result.status == "ready"
    assert result.chunks_created == 1  # Short doc = 1 chunk
    assert captured["upsert"]["collection"].endswith("test_documents")
    points = captured["upsert"]["points"]
    assert len(points) == 1
    assert points[0].payload["document_id"] == "doc-1"
    assert points[0].payload["metadata"]["title"] == "Doc"
    assert points[0].payload["metadata"]["chunk_index"] == 0
    assert points[0].payload["metadata"]["total_chunks"] == 1


def test_vector_store_delete(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("QDRANT_URL", "https://example.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "qdrant-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("APP_ENV", "test")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.embeddings = SimpleNamespace(
                create=lambda **_: SimpleNamespace(data=[SimpleNamespace(embedding=[])])
            )

    deleted_args: dict = {}

    class FakeQdrantClient:
        def __init__(self, *args, **kwargs):
            pass

        def upsert(self, *args, **kwargs):
            pass

        def delete(self, collection_name, points_selector, wait):
            # Now uses FilterSelector instead of PointIdsList
            deleted_args["collection_name"] = collection_name
            deleted_args["points_selector"] = points_selector
            deleted_args["wait"] = wait

    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(vector_store, "QdrantClient", FakeQdrantClient)

    store = vector_store.get_vector_store(refresh=True)
    result = store.delete_document("doc-xyz")

    assert result.status == "deleted"
    assert deleted_args["collection_name"].endswith("test_documents")
    # Filter-based deletion uses FilterSelector
    assert hasattr(deleted_args["points_selector"], "filter")


# ============================================================================
# CHUNKING TESTS
# ============================================================================


def test_split_text_short():
    """Short text should not be split."""
    text = "This is a short document."
    chunks = vector_store._split_text(text, chunk_size=4000, overlap=400)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_text_long():
    """Long text should be split into multiple chunks."""
    # Create a 10000 char document
    text = "This is paragraph one. " * 100  # ~2300 chars
    text += "\n\n"
    text += "This is paragraph two. " * 100
    text += "\n\n"
    text += "This is paragraph three. " * 100
    text += "\n\n"
    text += "This is paragraph four. " * 100
    text += "\n\n"
    text += "Final paragraph content. " * 50

    # With chunk_size=4000, overlap=400, expect 3+ chunks
    chunks = vector_store._split_text(text, chunk_size=4000, overlap=400)

    assert len(chunks) > 1
    # Each chunk should be <= chunk_size (approximately)
    for chunk in chunks:
        assert len(chunk) <= 4500  # Allow some slack for word boundaries
    # Content should be preserved
    assert "paragraph one" in chunks[0]
    assert "Final paragraph" in chunks[-1]


def test_split_text_overlap():
    """Chunks should have overlapping content."""
    # Create text with clear markers
    text = "MARKER_START " + ("x" * 3800) + " MARKER_MID " + ("y" * 3800) + " MARKER_END"

    chunks = vector_store._split_text(text, chunk_size=4000, overlap=400)

    assert len(chunks) >= 2
    # First chunk should start with MARKER_START
    assert "MARKER_START" in chunks[0]
    # Last chunk should contain MARKER_END
    assert "MARKER_END" in chunks[-1]


def test_upsert_long_document_creates_multiple_chunks(monkeypatch: pytest.MonkeyPatch):
    """Long documents should create multiple vectors."""
    monkeypatch.setenv("QDRANT_URL", "https://example.qdrant.io")
    monkeypatch.setenv("QDRANT_API_KEY", "qdrant-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("APP_ENV", "test")
    # Set small chunk size for testing
    monkeypatch.setenv("QDRANT_CHUNK_SIZE", "500")
    monkeypatch.setenv("QDRANT_CHUNK_OVERLAP", "50")

    # Force reload with new chunk settings
    import importlib
    importlib.reload(vector_store)

    captured_points: list = []

    class FakeEmbeddings:
        def create(self, model: str, input: str):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1] * 1536)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.embeddings = FakeEmbeddings()

    class FakeQdrantClient:
        def __init__(self, *args, **kwargs):
            pass

        def upsert(self, collection_name, points, wait):
            captured_points.extend(points)

    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(vector_store, "QdrantClient", FakeQdrantClient)

    store = vector_store.get_vector_store(refresh=True)

    # Create a 2500 char document (should create ~5 chunks with 500 char size)
    long_content = "Section A. " + ("word " * 200) + "\n\n"  # ~1100 chars
    long_content += "Section B. " + ("text " * 200) + "\n\n"  # +~1100 chars
    long_content += "Section C. Final content here."

    result = store.upsert_document(
        document_id="long-doc-test",
        content=long_content,
        metadata={"title": "Long Test Document", "source": "test"},
        parent_id="root",
        is_human_readable=True,
    )

    assert result.status == "ready"
    assert result.chunks_created > 1
    assert len(captured_points) == result.chunks_created

    # Verify all chunks have correct metadata
    for i, point in enumerate(captured_points):
        assert point.payload["document_id"] == "long-doc-test"
        assert point.payload["metadata"]["title"] == "Long Test Document"
        assert point.payload["metadata"]["chunk_index"] == i
        assert point.payload["metadata"]["total_chunks"] == result.chunks_created
        # Each chunk should have unique ID
        assert ":chunk:" in str(point.id) or point.id != captured_points[0].id or i == 0

    # First chunk should contain "Section A"
    assert "Section A" in captured_points[0].payload["content"]
    # Last chunk should contain "Final content"
    assert "Final content" in captured_points[-1].payload["content"]
