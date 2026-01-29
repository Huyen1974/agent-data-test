"""Utilities for writing knowledge vectors to Qdrant."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid5, NAMESPACE_DNS

# Chunking configuration (configurable via environment variables)
CHUNK_SIZE = int(os.getenv("QDRANT_CHUNK_SIZE", "4000"))
CHUNK_OVERLAP = int(os.getenv("QDRANT_CHUNK_OVERLAP", "400"))

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


@dataclass(slots=True)
class VectorSyncResult:
    status: str
    error: str | None = None
    chunks_created: int = 0


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks.

    Uses a simple character-based splitter that tries to break on paragraph
    boundaries (\n\n), then sentence boundaries (. ), then word boundaries.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If we're not at the end, try to find a good break point
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2  # Include the newlines
            else:
                # Look for sentence break
                sentence_break = text.rfind(". ", start, end)
                if sentence_break > start + chunk_size // 2:
                    end = sentence_break + 2
                else:
                    # Look for word break
                    word_break = text.rfind(" ", start, end)
                    if word_break > start + chunk_size // 2:
                        end = word_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


class QdrantVectorStore:
    """Thin wrapper around Qdrant upsert/delete operations."""

    def __init__(self) -> None:
        env = os.getenv("APP_ENV") or os.getenv("ENV") or "test"
        # Allow overriding collection explicitly; otherwise follow LAW: <env>_documents
        default_collection = f"{env}_documents"
        self.collection = os.getenv("QDRANT_COLLECTION", default_collection)
        self.url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_API_URL")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
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
        """Upsert document with automatic chunking for long content.

        Documents longer than CHUNK_SIZE are split into overlapping chunks.
        Each chunk gets a unique point_id but shares the same document_id
        in metadata for retrieval grouping.
        """
        if not self.enabled:
            return VectorSyncResult(status="skipped")
        try:
            self._ensure_client()
            if self._client is None:
                raise RuntimeError("Qdrant client unavailable")

            # Split content into chunks
            chunks = _split_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
            total_chunks = len(chunks)

            # Preserve original metadata with source info
            base_metadata = metadata or {}
            if "source_id" not in base_metadata and "title" not in base_metadata:
                # Ensure source tracking for citation integrity
                base_metadata["source_id"] = document_id

            points: list[Any] = []
            for idx, chunk_text in enumerate(chunks):
                embedding = self._embed(chunk_text)

                # Build payload with chunk metadata
                payload = {
                    "content": chunk_text,  # Required by langroid Document class
                    "document_id": document_id,
                    "metadata": {
                        **base_metadata,
                        "chunk_index": idx,
                        "total_chunks": total_chunks,
                    },
                    "parent_id": parent_id,
                    "is_human_readable": is_human_readable,
                }

                # Generate unique point_id for each chunk
                # Format: uuid5(document_id:chunk_idx) for deterministic IDs
                chunk_id = f"{document_id}:chunk:{idx}"
                point_id = str(uuid5(NAMESPACE_DNS, chunk_id))

                points.append(
                    qmodels.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                )

            # Batch upsert all chunks
            self._client.upsert(
                collection_name=self.collection,
                points=points,
                wait=True,
            )

            logger.info(
                "Upserted %d chunk(s) for document %s", total_chunks, document_id
            )
            return VectorSyncResult(status="ready", chunks_created=total_chunks)
        except Exception as exc:  # pragma: no cover - network/SDK errors
            logger.error("Failed to upsert vector for %s: %s", document_id, exc)
            return VectorSyncResult(status="error", error=str(exc))

    def delete_document(self, document_id: str) -> VectorSyncResult:
        """Delete all chunks for a document.

        Uses filter-based deletion to remove all points matching the document_id,
        handling both single-vector documents and chunked documents.
        """
        if not self.enabled:
            return VectorSyncResult(status="skipped")
        try:
            self._ensure_client()
            if self._client is None:
                raise RuntimeError("Qdrant client unavailable")

            # Delete by filter on document_id to handle all chunks
            filter_condition = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            )
            self._client.delete(
                collection_name=self.collection,
                points_selector=qmodels.FilterSelector(filter=filter_condition),
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
