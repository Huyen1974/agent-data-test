"""Utilities for writing knowledge vectors to Qdrant."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from gcp_secrets import SecretAccessError, get_secret

try:  # pragma: no cover - optional dependency import guard
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:  # pragma: no cover - optional dependency import guard
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models as qmodels  # type: ignore
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore
    qmodels = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_QDRANT_SECRET = "Qdrant_agent_data_N1D8R2vC0_5"
DEFAULT_OPENAI_SECRET = "openai-api-key-sg"


@dataclass(slots=True)
class VectorSyncResult:
    status: str
    error: str | None = None


def _load_secret(env_key: str, secret_env_key: str, default_secret: str) -> str | None:
    direct = os.getenv(env_key)
    if direct:
        return direct
    secret_name = os.getenv(secret_env_key, default_secret)
    if not secret_name:
        return None
    try:
        return get_secret(secret_name)
    except SecretAccessError as exc:  # pragma: no cover - network errors
        logger.error("Failed to load secret %s: %s", secret_name, exc)
        return None


class QdrantVectorStore:
    """Thin wrapper around Qdrant upsert/delete operations."""

    def __init__(self) -> None:
        env = os.getenv("APP_ENV") or os.getenv("ENV") or "test"
        # Allow overriding collection explicitly; otherwise follow LAW: <env>_documents
        default_collection = f"{env}_documents"
        self.collection = os.getenv("QDRANT_COLLECTION", default_collection)
        self.url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_API_URL")
        self.api_key = _load_secret(
            "QDRANT_API_KEY", "QDRANT_API_SECRET_NAME", DEFAULT_QDRANT_SECRET
        )
        self.openai_key = _load_secret(
            "OPENAI_API_KEY", "OPENAI_API_SECRET_NAME", DEFAULT_OPENAI_SECRET
        )
        self.embedding_model = os.getenv("QDRANT_EMBED_MODEL", "text-embedding-3-small")
        self.enabled = all(
            [
                self.collection,
                self.url,
                self.api_key,
                self.openai_key,
                OpenAI is not None,
                QdrantClient is not None,
                qmodels is not None,
            ]
        )
        self._client: QdrantClient | None = None
        self._openai: OpenAI | None = None

        if not self.enabled:
            missing = []
            if not self.url:
                missing.append("QDRANT_URL")
            if not self.api_key:
                missing.append("QDRANT_API_KEY")
            if not self.openai_key:
                missing.append("OPENAI_API_KEY")
            if OpenAI is None:
                missing.append("openai-sdk")
            if QdrantClient is None:
                missing.append("qdrant-client")
            if missing:
                logger.info(
                    "Qdrant vector store disabled; missing dependencies/env: %s",
                    ", ".join(missing),
                )

    def _ensure_client(self) -> None:
        if not self.enabled:
            return
        if self._client is None:
            self._client = QdrantClient(  # type: ignore[call-arg]
                url=self.url,
                api_key=self.api_key,
                timeout=15,
            )
        if self._openai is None:
            # Allow overriding OpenAI base URL for testing
            openai_base = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
            kwargs = {"api_key": self.openai_key}
            if openai_base:
                kwargs["base_url"] = openai_base
            self._openai = OpenAI(**kwargs)  # type: ignore[arg-type]

    def _embed(self, text: str) -> list[float]:
        self._ensure_client()
        if not self.enabled or self._openai is None:
            raise RuntimeError("Vector store not enabled")
        truncated = text[:6000]
        response = self._openai.embeddings.create(
            model=self.embedding_model,
            input=truncated,
        )
        return list(response.data[0].embedding)

    def upsert_document(
        self,
        *,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        parent_id: str | None = None,
        is_human_readable: bool = False,
    ) -> VectorSyncResult:
        if not self.enabled:
            return VectorSyncResult(status="skipped")
        try:
            self._ensure_client()
            if self._client is None:
                raise RuntimeError("Qdrant client unavailable")
            embedding = self._embed(content)
            payload = {
                "document_id": document_id,
                "metadata": metadata or {},
                "parent_id": parent_id,
                "is_human_readable": is_human_readable,
            }
            point = qmodels.PointStruct(
                id=document_id,
                vector=embedding,
                payload=payload,
            )
            self._client.upsert(
                collection_name=self.collection,
                points=[point],
                wait=True,
            )
            return VectorSyncResult(status="ready")
        except Exception as exc:  # pragma: no cover - network/SDK errors
            logger.error("Failed to upsert vector for %s: %s", document_id, exc)
            return VectorSyncResult(status="error", error=str(exc))

    def delete_document(self, document_id: str) -> VectorSyncResult:
        if not self.enabled:
            return VectorSyncResult(status="skipped")
        try:
            self._ensure_client()
            if self._client is None:
                raise RuntimeError("Qdrant client unavailable")
            selector = qmodels.PointIdsList(points=[document_id])
            self._client.delete(
                collection_name=self.collection,
                points_selector=selector,
                wait=True,
            )
            return VectorSyncResult(status="deleted")
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to delete vector for %s: %s", document_id, exc)
            return VectorSyncResult(status="error", error=str(exc))


_cached_store: QdrantVectorStore | None = None


def get_vector_store(refresh: bool = False) -> QdrantVectorStore:
    global _cached_store
    if refresh or _cached_store is None:
        _cached_store = QdrantVectorStore()
    return _cached_store


def ensure_vector_store_enabled() -> bool:
    return get_vector_store().enabled


def upsert_documents(
    updates: Iterable[tuple[str, str, dict[str, Any] | None, str | None, bool]],
) -> VectorSyncResult:
    store = get_vector_store()
    result = VectorSyncResult(status="skipped")
    for doc_id, content, metadata, parent_id, is_hr in updates:
        result = store.upsert_document(
            document_id=doc_id,
            content=content,
            metadata=metadata,
            parent_id=parent_id,
            is_human_readable=is_hr,
        )
        if result.status == "error":
            break
    return result


def delete_document(document_id: str) -> VectorSyncResult:
    store = get_vector_store()
    return store.delete_document(document_id)
