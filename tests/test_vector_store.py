from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent_data import vector_store
from gcp_secrets import SecretAccessError


@pytest.fixture(autouse=True)
def reset_vector_store():
    vector_store.get_vector_store(refresh=True)
    yield
    vector_store.get_vector_store(refresh=True)


@pytest.fixture
def mock_secrets(monkeypatch: pytest.MonkeyPatch):
    values = {}

    def fake_get_secret(name: str, **_):
        if name in values:
            return values[name]
        raise SecretAccessError(f"secret {name} unavailable")

    monkeypatch.setattr(vector_store, "get_secret", fake_get_secret)
    return values


def test_vector_store_disabled_without_env(
    monkeypatch: pytest.MonkeyPatch, mock_secrets
):
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


def test_vector_store_upsert_success(monkeypatch: pytest.MonkeyPatch, mock_secrets):
    monkeypatch.setenv("QDRANT_URL", "https://example.qdrant.io")
    mock_secrets["Qdrant_agent_data_N1D8R2vC0_5"] = "qdrant-key"
    mock_secrets["openai-api-key-sg"] = "openai-key"
    monkeypatch.setenv("APP_ENV", "test")

    captured: dict[str, MagicMock] = {}

    class FakeEmbeddings:
        def create(self, model: str, input: str):
            assert model == "text-embedding-3-small"
            assert input.startswith("Document body")
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
    assert captured["upsert"]["collection"].endswith("test_documents")
    points = captured["upsert"]["points"]
    assert points[0].id == "doc-1"
    assert points[0].payload["metadata"]["title"] == "Doc"


def test_vector_store_delete(monkeypatch: pytest.MonkeyPatch, mock_secrets):
    monkeypatch.setenv("QDRANT_URL", "https://example.qdrant.io")
    mock_secrets["Qdrant_agent_data_N1D8R2vC0_5"] = "qdrant-key"
    mock_secrets["openai-api-key-sg"] = "openai-key"
    monkeypatch.setenv("APP_ENV", "test")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.embeddings = SimpleNamespace(
                create=lambda **_: SimpleNamespace(data=[SimpleNamespace(embedding=[])])
            )

    class FakeQdrantClient:
        def __init__(self, *args, **kwargs):
            self.deleted = None

        def upsert(self, *args, **kwargs):
            pass

        def delete(self, collection_name, points_selector, wait):
            self.deleted = (collection_name, points_selector.points, wait)

    fake_client = FakeQdrantClient()
    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(vector_store, "QdrantClient", lambda *_, **__: fake_client)

    store = vector_store.get_vector_store(refresh=True)
    store.delete_document("doc-xyz")
    assert fake_client.deleted[0].endswith("test_documents")
    assert fake_client.deleted[1] == ["doc-xyz"]
