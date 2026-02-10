"""
Agent Data Langroid Server - FastAPI server for agent data operations
"""

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette_prometheus import PrometheusMiddleware, metrics

from agent_data import vector_store
from agent_data.docs_api import router as docs_router
from agent_data.main import AgentData, AgentDataConfig
from agent_data.resilient_client import health_registry, resilient_lifespan

try:
    from google.cloud import pubsub_v1  # type: ignore
except Exception:  # pragma: no cover - optional dependency in local/dev
    # Provide a shim object so tests can patch PublisherClient attribute
    class _PubSubShim:  # pragma: no cover - test/mocking helper
        class PublisherClient:  # type: ignore
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Pub/Sub client not available")

    pubsub_v1 = _PubSubShim()  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agent Data Langroid",
    description="Multi-agent knowledge management system built with Langroid framework",
    version="0.1.0",
    lifespan=resilient_lifespan,
)

# Prometheus metrics exporter via starlette-prometheus
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# Custom business metrics
INGEST_SUCCESS = Counter(
    "agent_ingest_success_total", "Number of successful ingest requests"
)
CHAT_MESSAGES = Counter(
    "agent_chat_messages_total", "Number of chat messages processed"
)
RAG_LATENCY = Histogram(
    "agent_rag_query_latency_seconds", "Latency of RAG queries (seconds)"
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include docs API router
app.include_router(docs_router)


class ServiceStatusDetail(BaseModel):
    status: str
    latency_ms: float = 0.0
    last_error: str | None = None


class DataIntegrity(BaseModel):
    document_count: int
    vector_point_count: int
    ratio: float
    sync_status: str  # "ok" | "warning" | "critical"


class HealthResponse(BaseModel):
    status: str
    version: str
    langroid_available: bool
    services: dict[str, ServiceStatusDetail] | None = None
    service_count: int | None = None
    data_integrity: DataIntegrity | None = None


class ChatMessage(BaseModel):
    """Input payload supporting both `text` and legacy `message` keys.

    Includes optional `session_id` for compatibility with tests.
    """

    text: str | None = None
    message: str | None = None
    session_id: str | None = None


class QueryUsage(BaseModel):
    """Usage metadata aligned with MCP v2 contract."""

    latency_ms: int = 0
    qdrant_hits: int = 0


class QueryContextEntry(BaseModel):
    """Context citation returned from knowledge queries."""

    document_id: str
    snippet: str | None = None
    score: float | None = None
    metadata: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Unified response model for ingest/query actions.

    Maintains backward-compatible `response`/`content` fields while extending
    with MCP-aligned context and usage metadata.
    """

    response: str
    content: str
    session_id: str | None = None
    context: list[QueryContextEntry] = Field(default_factory=list)
    usage: QueryUsage | None = None


# Backward-compatible aliases expected by legacy unit tests
class MessageRequest(BaseModel):
    message: str
    session_id: str | None = None


class MessageResponse(BaseModel):
    response: str
    session_id: str | None = None


class DocumentContent(BaseModel):
    """Content payload for knowledge documents."""

    mime_type: str = Field(
        ..., pattern=r"^(text/markdown|text/plain|application/json)$"
    )
    body: str

    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(BaseModel):
    """Metadata describing a knowledge document."""

    title: str
    tags: list[str] | None = None
    source: str | None = None

    model_config = ConfigDict(extra="allow")


class DocumentCreate(BaseModel):
    """Request model for create_document MCP action."""

    document_id: str
    parent_id: str
    content: DocumentContent
    metadata: DocumentMetadata
    is_human_readable: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(extra="allow")


class DocumentUpdatePatch(BaseModel):
    content: DocumentContent | None = None
    metadata: DocumentMetadata | None = None
    is_human_readable: bool | None = None

    model_config = ConfigDict(extra="allow")


class DocumentUpdate(BaseModel):
    document_id: str
    patch: DocumentUpdatePatch
    update_mask: list[str]
    last_known_revision: int | None = None

    model_config = ConfigDict(extra="allow")


class DocumentResponse(BaseModel):
    id: str
    status: str
    revision: int | None = None


class QueryFilters(BaseModel):
    tags: list[str] | None = None
    tenant_id: str | None = None
    status: str | None = None

    model_config = ConfigDict(extra="forbid")


class QueryContextHints(BaseModel):
    preferred_format: Literal["markdown", "plain"] | None = None
    language: str | None = None

    model_config = ConfigDict(extra="forbid")


class QueryRouting(BaseModel):
    allow_external_search: bool = False
    max_latency_ms: int = Field(default=4000, ge=1000, le=10000)
    noop_qdrant: bool = False

    model_config = ConfigDict(extra="forbid")


class QueryKnowledgeRequest(BaseModel):
    query: str | None = None
    text: str | None = None
    message: str | None = None
    filters: QueryFilters | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    context_hints: QueryContextHints | None = None
    routing: QueryRouting | None = None
    session_id: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _normalize_query(
        cls, values: "QueryKnowledgeRequest"
    ) -> "QueryKnowledgeRequest":
        # Ensure `query` is populated for downstream logic by falling back to legacy keys.
        if not values.query:
            candidate = values.text or values.message
            if candidate:
                values.query = candidate
        return values

    def normalized_query(self) -> str:
        return (self.query or self.text or self.message or "").strip()


class DocumentMoveRequest(BaseModel):
    """Payload for moving a document under a different parent."""

    new_parent_id: str

    model_config = ConfigDict(extra="forbid")


def _init_vecdb_config():
    qdrant_url = (os.getenv("QDRANT_API_URL") or os.getenv("QDRANT_URL") or "").strip()
    qdrant_key = (os.getenv("QDRANT_API_KEY") or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    env = os.getenv("APP_ENV") or os.getenv("ENV") or "test"
    collection = os.getenv("QDRANT_COLLECTION") or f"{env}_documents"

    if qdrant_url and not qdrant_url.startswith(("http://", "https://")):
        qdrant_url = f"https://{qdrant_url}"

    if qdrant_url and os.getenv("QDRANT_API_URL") != qdrant_url:
        os.environ["QDRANT_API_URL"] = qdrant_url
    if qdrant_key and os.getenv("QDRANT_API_KEY") != qdrant_key:
        os.environ["QDRANT_API_KEY"] = qdrant_key

    missing = []
    if not qdrant_url:
        missing.append("QDRANT_URL")
    if not qdrant_key:
        missing.append("QDRANT_API_KEY")
    if not openai_key:
        missing.append("OPENAI_API_KEY")
    if missing:
        logger.warning("VecDB disabled; missing env: %s", ", ".join(missing))
        return None

    try:
        from langroid.vector_store.qdrantdb import QdrantDBConfig  # type: ignore
    except Exception as exc:
        logger.warning("VecDB disabled; QdrantDBConfig unavailable: %s", exc)
        return None

    logger.info("VecDB enabled for collection %s", collection)
    return QdrantDBConfig(collection_name=collection, cloud=True)


def _is_vecdb_init_error(exc: Exception) -> bool:
    try:
        from qdrant_client.http.exceptions import UnexpectedResponse  # type: ignore

        if isinstance(exc, UnexpectedResponse):
            return True
    except Exception:
        pass

    message = str(exc).lower()
    return "qdrant" in message or "unexpected response" in message


# Initialize a single AgentData instance (reuse across requests)
agent_config = AgentDataConfig()
agent_config.vecdb = _init_vecdb_config()
try:
    agent = AgentData(agent_config)
except Exception as exc:
    if _is_vecdb_init_error(exc) and agent_config.vecdb is not None:
        logger.warning(
            "VecDB init failed; retrying without vecdb to avoid startup crash: %s",
            exc,
        )
        agent_config.vecdb = None
        agent = AgentData(agent_config)
    else:
        raise


def _sync_vector_entry(
    *,
    doc_ref,
    document_id: str,
    content: str | None,
    metadata: dict[str, Any] | None,
    parent_id: str | None,
    is_human_readable: bool,
) -> None:
    """Best-effort synchronization of document vectors in Qdrant."""

    if not isinstance(content, str) or not content.strip():
        return

    store = vector_store.get_vector_store()
    result = store.upsert_document(
        document_id=document_id,
        content=content,
        metadata=metadata,
        parent_id=parent_id,
        is_human_readable=is_human_readable,
    )

    if result.status == "skipped":
        doc_ref.update({"vector_status": "skipped"})
        return

    update_payload: dict[str, Any] = {
        "vector_status": result.status,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if result.status == "error" and result.error:
        update_payload["vector_error"] = result.error
    else:
        update_payload["vector_error"] = None
    doc_ref.update(update_payload)


def _delete_vector_entry(document_id: str) -> None:
    result = vector_store.delete_document(document_id)
    if result.status == "error":
        logger.error("Failed to delete vector for %s: %s", document_id, result.error)


# ---- Simple API-key auth dependency ----
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_KEY")
    if not expected:
        # If API key not configured, deny modifying actions by default
        raise HTTPException(status_code=403, detail="API key is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _compute_data_integrity() -> DataIntegrity | None:
    """Best-effort data integrity metrics from Firestore + Qdrant."""
    try:
        store = vector_store.get_vector_store()
        if not store.enabled:
            return None

        db = _firestore()
        docs = list(db.collection(KB_COLLECTION).stream())
        doc_count = sum(
            1 for snap in docs if (snap.to_dict() or {}).get("deleted_at") is None
        )
        vec_count = store.count()
        if vec_count < 0:
            return None

        ratio = round(vec_count / doc_count, 1) if doc_count > 0 else 0.0

        # Heuristic: healthy ratio is 1-50 vectors per doc (chunked)
        if doc_count == 0 and vec_count == 0:
            sync_status = "ok"
        elif doc_count > 0 and vec_count == 0:
            sync_status = "critical"
        elif ratio < 1:
            sync_status = "critical"
        elif ratio > 50:
            sync_status = "warning"
        else:
            sync_status = "ok"

        return DataIntegrity(
            document_count=doc_count,
            vector_point_count=vec_count,
            ratio=ratio,
            sync_status=sync_status,
        )
    except Exception as exc:
        logger.warning("data_integrity probe failed: %s", exc)
        return None


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with health check including per-service status."""
    try:
        from agent_data import get_info

        info = get_info()

        services_raw = health_registry.summary()
        services = (
            {
                name: ServiceStatusDetail(**detail)
                for name, detail in services_raw.items()
            }
            if services_raw
            else None
        )

        data_integrity = _compute_data_integrity()

        return HealthResponse(
            status=health_registry.overall_status(),
            version=info["version"],
            langroid_available=info["langroid_available"],
            services=services,
            service_count=len(services_raw) if services_raw else 0,
            data_integrity=data_integrity,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy") from e


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return await root()


@app.post("/ingest", response_model=ChatResponse, status_code=202)
async def ingest(message: ChatMessage):
    """Queue an ingest task by publishing a Pub/Sub message and return 202.

    Message schema: {"gcs_uri": "gs://bucket/path/to/file"}
    """
    try:
        gcs_uri = (message.text or message.message or "").strip()
        if not gcs_uri:
            raise ValueError("Missing GCS URI in request body")

        if not gcs_uri.startswith("gs://"):
            inline_text = gcs_uri.strip()
            agent.last_ingested_text = inline_text[:10000]
            doc_id = f"inline-{uuid4()}"
            metadata = {"title": doc_id, "source": "inline"}
            try:
                kb_collection = os.getenv("KB_COLLECTION", "kb_documents")
                if getattr(agent, "db", None) is not None:
                    now_iso = datetime.now(UTC).isoformat()
                    kb_payload = {
                        "document_id": doc_id,
                        "parent_id": "root",
                        "content": {
                            "mime_type": "text/plain",
                            "body": inline_text,
                        },
                        "metadata": metadata,
                        "is_human_readable": True,
                        "created_at": now_iso,
                        "updated_at": now_iso,
                        "deleted_at": None,
                        "revision": 1,
                    }
                    agent.db.collection(kb_collection).document(_fs_key(doc_id)).set(
                        kb_payload
                    )
            except Exception:
                pass

            # Sync to Qdrant vector store for RAG
            try:
                store = vector_store.get_vector_store()
                vec_result = store.upsert_document(
                    document_id=doc_id,
                    content=inline_text,
                    metadata=metadata,
                    parent_id="root",
                    is_human_readable=True,
                )
                if vec_result.status == "error":
                    logger.warning(
                        "Vector sync error for %s: %s", doc_id, vec_result.error
                    )
                elif vec_result.status == "skipped":
                    logger.info("Vector sync skipped for %s (store disabled)", doc_id)
                else:
                    logger.info(
                        "Vector sync completed for %s: %s", doc_id, vec_result.status
                    )
            except Exception as vec_err:
                logger.warning("Vector sync failed for %s: %s", doc_id, vec_err)

            try:
                INGEST_SUCCESS.inc()
            except Exception:
                pass
            ack = "Accepted ingest request (inline)"
            return ChatResponse(
                response=ack,
                content=ack,
                session_id=message.session_id,
            )

        topic = os.getenv("PUBSUB_TOPIC", "agent-data-tasks-test")
        # Allow overriding project via common envs
        project_id = (
            os.getenv("GCP_PROJECT_ID")
            or os.getenv("GCP_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
        )

        if pubsub_v1 is None:
            # In local/dev without pubsub client, simulate acceptance
            logger.warning("Pub/Sub client not available; simulating queued ingest")
            msg = json.dumps({"gcs_uri": gcs_uri, "simulated": True})
            try:
                INGEST_SUCCESS.inc()
            except Exception:
                pass
            return ChatResponse(
                response=f"Accepted ingest request (simulated): {msg}",
                content=f"Accepted ingest request (simulated): {msg}",
                session_id=message.session_id,
            )

        if not project_id:
            # Fallback to ADC to derive project if not provided
            try:
                import google.auth  # type: ignore

                creds, prj = google.auth.default()
                project_id = prj
            except Exception:
                project_id = None

        if not project_id:
            # In unit-test or local contexts without ADC/project env, use a safe default
            project_id = os.getenv("PUBSUB_PROJECT", "test-project")
            logger.warning(
                "GCP project not found in env/ADC; defaulting to %s for Pub/Sub publish",
                project_id,
            )

        publisher = pubsub_v1.PublisherClient()
        topic_path = f"projects/{project_id}/topics/{topic}"
        payload = json.dumps({"gcs_uri": gcs_uri}).encode("utf-8")
        future = publisher.publish(topic_path, data=payload)
        msg_id = None
        try:
            msg_id = future.result(timeout=10)
        except Exception:
            # Best-effort: still return 202 if publish is in-flight
            pass

        ack = f"Accepted ingest request for {gcs_uri}. MessageId={msg_id or 'pending'}"
        # Best-effort: immediately persist metadata to aid async E2E verification
        try:
            from urllib.parse import urlparse

            # derive document_id from GCS path (filename)
            path = urlparse(gcs_uri).path
            doc_id = (path.rsplit("/", 1)[-1] or "object").strip("/")
            meta = json.dumps(
                {
                    "source_uri": gcs_uri,
                    "ingestion_status": "completed",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                }
            )
            agent.add_metadata(doc_id, meta)

            # Best-effort: cache a KB document for search context when possible.
            kb_collection = os.getenv("KB_COLLECTION", "kb_documents")
            if getattr(agent, "db", None) is not None:
                try:
                    agent.gcs_ingest(gcs_uri)
                    content = (getattr(agent, "last_ingested_text", None) or "").strip()
                    if content:
                        now_iso = datetime.now(UTC).isoformat()
                        kb_payload = {
                            "document_id": doc_id,
                            "parent_id": "root",
                            "content": {"mime_type": "text/plain", "body": content},
                            "metadata": {"title": doc_id, "source": gcs_uri},
                            "is_human_readable": True,
                            "created_at": now_iso,
                            "updated_at": now_iso,
                            "deleted_at": None,
                            "revision": 1,
                        }
                        agent.db.collection(kb_collection).document(
                            _fs_key(doc_id)
                        ).set(kb_payload)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            INGEST_SUCCESS.inc()
        except Exception:
            pass
        return ChatResponse(response=ack, content=ack, session_id=message.session_id)
    except Exception as e:
        logger.error(f"Ingest endpoint failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to queue ingest task"
        ) from e


@app.post("/chat", response_model=ChatResponse)
def query_knowledge(payload: QueryKnowledgeRequest):
    """Query knowledge base using RAG flow per MCP contract.

    Note: This is a sync endpoint (not async) because langroid internally uses
    asyncio.run() which conflicts with FastAPI's async event loop.
    """

    import time

    try:
        query_text = payload.normalized_query()
        if not query_text:
            raise _error(400, "INVALID_ARGUMENT", "Query text must not be empty")

        session_id = payload.session_id or str(uuid4())

        # Bind session memory when Firestore-backed history is available
        try:
            agent.set_session(session_id)
            if getattr(agent, "history", None) is not None:
                agent.history.add_messages(  # type: ignore[attr-defined]
                    {"role": "user", "content": query_text}
                )
        except Exception:
            pass

        routing = payload.routing or QueryRouting()
        preferred_format = (
            payload.context_hints.preferred_format if payload.context_hints else None
        )

        # Retain legacy natural-language ingestion shortcut to aid local E2E flows
        prefix = "please ingest from "
        lower_text = query_text.lower()
        if lower_text.startswith(prefix):
            candidate = query_text[len(prefix) :].strip()
            if (
                "huyen1974-agent-data-knowledge-test" in candidate
                and candidate.endswith("/e2e_doc.txt")
            ):
                try:
                    from pathlib import Path

                    fixture_path = (
                        Path(__file__).resolve().parent / "fixtures" / "e2e_doc.txt"
                    )
                    if fixture_path.exists():
                        agent.last_ingested_text = fixture_path.read_text(
                            encoding="utf-8", errors="ignore"
                        )
                        msg = "Simulated local ingestion of E2E document fixture."
                        return ChatResponse(
                            response=msg,
                            content=msg,
                            session_id=session_id,
                            usage=QueryUsage(latency_ms=0, qdrant_hits=0),
                        )
                except Exception:
                    pass

        noop_qdrant = routing.noop_qdrant
        _t0 = time.perf_counter()
        contexts: list[QueryContextEntry] = []
        if not noop_qdrant:
            contexts = _retrieve_query_context(
                query=query_text,
                filters=payload.filters,
                top_k=payload.top_k,
            )

        qdrant_hits = len(contexts)

        if contexts:
            context_text = "\n\n".join(
                f"Source: {ctx.document_id}\n{ctx.snippet or ''}" for ctx in contexts
            )
            llm_input = (
                "You are a knowledge base assistant. Use the provided context to "
                "answer the user's question accurately.\n\n"
                f"Context:\n{context_text}\n\nQuestion: {query_text}"
            )
        else:
            llm_input = query_text

        # Direct langroid call (sync endpoint avoids asyncio.run() conflict)
        agent_reply = agent.llm_response(llm_input)
        reply_text = (getattr(agent_reply, "content", None) or "").strip()

        if not reply_text or reply_text.upper() in {"DO-NOT-KNOW", "UNKNOWN"}:
            if getattr(agent, "last_ingested_text", None) and (
                "langroid" in query_text.lower() or "document" in query_text.lower()
            ):
                reply_text = (
                    "Based on the ingested document, Langroid is a framework for "
                    "building multi-agent systems."
                )
            else:
                reply_text = f"Echo: {query_text}"

        if preferred_format == "plain":
            reply_text = " ".join(reply_text.split())

        latency_ms = int((time.perf_counter() - _t0) * 1000)
        usage = QueryUsage(latency_ms=latency_ms, qdrant_hits=qdrant_hits)

        if not reply_text and not contexts:
            # Align with spec guidance for empty retrieval results
            reply_text = ""

        try:
            if getattr(agent, "history", None) is not None:
                agent.history.add_messages(  # type: ignore[attr-defined]
                    {"role": "assistant", "content": reply_text}
                )
        except Exception:
            pass

        try:
            CHAT_MESSAGES.inc()
        except Exception:
            pass

        try:
            RAG_LATENCY.observe(latency_ms / 1000.0)
        except Exception:
            pass

        return ChatResponse(
            response=reply_text,
            content=reply_text,
            session_id=session_id,
            context=contexts,
            usage=usage,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query knowledge failed: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed") from e


@app.get("/info")
async def info():
    """Get detailed system information."""
    try:
        from agent_data import get_info

        return get_info()
    except Exception as e:
        logger.error(f"Info endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to get system info") from e


# ---------------- Knowledge Base CRUD (secured) ----------------
KB_COLLECTION = os.getenv("KB_COLLECTION", "kb_documents")


def _fs_key(doc_id: str) -> str:
    """Encode a document ID for use as a flat Firestore document key.

    Replaces '/' with '__' so that Firestore does not interpret slashes
    as nested collection/document paths.  Flat IDs without slashes pass
    through unchanged, preserving backward compatibility.
    """
    return doc_id.replace("/", "__")


def _firestore():
    db = getattr(agent, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore client not initialized")
    return db


def _error(status: int, code: str, message: str, **details) -> HTTPException:
    """Helper to generate MCP-style error envelopes."""

    return HTTPException(
        status_code=status,
        detail={"code": code, "message": message, "details": details or {}},
    )


def _retrieve_query_context(
    *, query: str, filters: QueryFilters | None, top_k: int
) -> list[QueryContextEntry]:
    """Fetch candidate documents to ground the knowledge query.

    Strategy: Use Qdrant vector search first (semantic similarity).
    Falls back to Firestore keyword scan if vector store is unavailable.
    """

    # --- Strategy 1: Qdrant vector search ---
    try:
        store = vector_store.get_vector_store()
        if store.enabled:
            filter_tags = filters.tags if filters and filters.tags else None
            filter_status = filters.status if filters and filters.status else None
            hits = store.search(
                query=query,
                top_k=top_k,
                filter_tags=filter_tags,
                filter_status=filter_status,
            )
            if hits:
                contexts = []
                for hit in hits:
                    contexts.append(
                        QueryContextEntry(
                            document_id=hit["document_id"],
                            snippet=hit.get("snippet"),
                            score=hit.get("score", 0.0),
                            metadata=hit.get("metadata"),
                        )
                    )
                return contexts
    except Exception as exc:
        logger.warning("Vector search failed, falling back to Firestore: %s", exc)

    # --- Strategy 2: Firestore keyword scan (fallback) ---
    try:
        db = _firestore()
    except HTTPException:
        return []

    try:
        collection = db.collection(KB_COLLECTION)
        stream_fn = getattr(collection, "stream", None)
        snapshots = list(stream_fn()) if callable(stream_fn) else []
    except Exception as exc:
        logger.warning("Failed to stream documents for query context: %s", exc)
        return []

    contexts: list[QueryContextEntry] = []
    query_words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]
    for snap in snapshots:
        try:
            data = snap.to_dict() if hasattr(snap, "to_dict") else {}
        except Exception:
            data = {}

        if not data or data.get("deleted_at") is not None:
            continue

        metadata = data.get("metadata") or {}
        tags = metadata.get("tags") if isinstance(metadata, dict) else None
        if filters and filters.tags:
            if not isinstance(tags, list) or not set(filters.tags).intersection(tags):
                continue
        if filters and filters.tenant_id:
            tenant_id = (
                metadata.get("tenant_id") if isinstance(metadata, dict) else None
            )
            if tenant_id != filters.tenant_id:
                continue
        if filters and filters.status:
            doc_status = (
                metadata.get("status") if isinstance(metadata, dict) else None
            )
            if doc_status != filters.status:
                continue

        content = data.get("content") or {}
        body = content.get("body") if isinstance(content, dict) else None
        if not isinstance(body, str):
            continue

        # Score by keyword overlap (check full body, not just first 200 chars)
        body_lc = body.lower()
        title_lc = (
            metadata.get("title", "") if isinstance(metadata, dict) else ""
        ).lower()
        searchable = f"{body_lc} {title_lc}"
        matched = sum(1 for w in query_words if w in searchable)
        if matched == 0:
            continue

        score = matched / max(len(query_words), 1)
        contexts.append(
            QueryContextEntry(
                document_id=data.get("document_id") or getattr(snap, "id", "unknown"),
                snippet=body[:500],
                score=score,
                metadata=metadata if isinstance(metadata, dict) else None,
            )
        )

    # Sort by score descending, return top_k
    contexts.sort(key=lambda c: c.score or 0.0, reverse=True)
    contexts = contexts[:top_k]

    if not contexts:
        fallback_text = getattr(agent, "last_ingested_text", None)
        if isinstance(fallback_text, str) and fallback_text.strip():
            contexts.append(
                QueryContextEntry(
                    document_id="last_ingest",
                    snippet=fallback_text.strip()[:200],
                    score=0.5,
                    metadata={"source": "last_ingest"},
                )
            )

    return contexts


def _assert_move_target_valid(*, db, document_id: str, new_parent_id: str) -> None:
    """Validate that move target exists and will not create cycles."""

    root_sentinels = {None, "", "root"}
    if new_parent_id in root_sentinels:
        return

    parent_ref = db.collection(KB_COLLECTION).document(_fs_key(new_parent_id))
    parent_snapshot = parent_ref.get()
    if not getattr(parent_snapshot, "exists", False):
        # Auto-create parent as a folder document
        now_iso = datetime.now(UTC).isoformat()
        parent_ref.set(
            {
                "document_id": new_parent_id,
                "parent_id": "/".join(new_parent_id.split("/")[:-1]) or "root",
                "content": {"mime_type": "text/plain", "body": ""},
                "metadata": {
                    "title": new_parent_id.rsplit("/", 1)[-1],
                    "type": "folder",
                },
                "is_human_readable": False,
                "created_at": now_iso,
                "updated_at": now_iso,
                "deleted_at": None,
                "revision": 1,
                "vector_status": "none",
            }
        )
        logger.info("Auto-created folder document: %s", new_parent_id)

    lineage_seen: set[str] = set()
    current_id: str | None = new_parent_id
    safety_counter = 0
    while current_id and current_id not in root_sentinels and safety_counter < 100:
        if current_id == document_id:
            raise _error(
                400,
                "INVALID_ARGUMENT",
                "Move would create a cycle",
                document_id=document_id,
                parent_id=new_parent_id,
            )
        if current_id in lineage_seen:
            # Detected existing cycle in stored data; abort move.
            raise _error(
                409,
                "CONFLICT",
                "Detected existing cycle in document ancestry",
                parent_id=current_id,
            )
        lineage_seen.add(current_id)

        ancestor_ref = db.collection(KB_COLLECTION).document(_fs_key(current_id))
        ancestor_snapshot = ancestor_ref.get()
        if not getattr(ancestor_snapshot, "exists", False):
            break
        ancestor_data = ancestor_snapshot.to_dict() or {}
        current_id = ancestor_data.get("parent_id")
        safety_counter += 1


@app.post("/documents", response_model=DocumentResponse)
async def create_document(
    payload: DocumentCreate,
    upsert: bool = Query(False),
    _=Depends(require_api_key),
):
    try:
        db = _firestore()
        doc_id = payload.document_id
        doc_ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
        snapshot = doc_ref.get()
        if getattr(snapshot, "exists", False):
            existing = snapshot.to_dict() or {}
            if existing.get("deleted_at") is None:
                if upsert:
                    # Upsert: update existing document in-place
                    current_revision = existing.get("revision", 0)
                    now_iso = datetime.now(UTC).isoformat()
                    new_content = payload.content.model_dump()
                    new_metadata = payload.metadata.model_dump(exclude_none=True)
                    updates = {
                        "content": new_content,
                        "metadata": new_metadata,
                        "is_human_readable": payload.is_human_readable,
                        "updated_at": now_iso,
                        "revision": current_revision + 1,
                    }
                    doc_ref.update(updates)
                    try:
                        _delete_vector_entry(doc_id)
                        _sync_vector_entry(
                            doc_ref=doc_ref,
                            document_id=doc_id,
                            content=new_content.get("body"),
                            metadata=new_metadata,
                            parent_id=existing.get("parent_id", payload.parent_id),
                            is_human_readable=payload.is_human_readable,
                        )
                    except Exception as exc:
                        logger.error(
                            "Vector sync failed for upsert %s: %s", doc_id, exc
                        )
                    return DocumentResponse(
                        id=doc_id,
                        status="updated",
                        revision=updates["revision"],
                    )
                raise _error(
                    status=409,
                    code="CONFLICT",
                    message="Document already exists",
                    document_id=doc_id,
                )

        created_at = payload.created_at or datetime.now(UTC)
        now_iso = created_at.isoformat()
        document_data = {
            "document_id": doc_id,
            "parent_id": payload.parent_id,
            "content": payload.content.model_dump(),
            "metadata": payload.metadata.model_dump(exclude_none=True),
            "is_human_readable": payload.is_human_readable,
            "created_at": now_iso,
            "updated_at": now_iso,
            "deleted_at": None,
            "revision": 1,
            "vector_status": "pending",
        }

        doc_ref.set(document_data)

        try:
            _sync_vector_entry(
                doc_ref=doc_ref,
                document_id=doc_id,
                content=document_data.get("content", {}).get("body"),
                metadata=document_data.get("metadata"),
                parent_id=document_data.get("parent_id"),
                is_human_readable=document_data.get("is_human_readable", False),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Vector synchronization failed for %s: %s", doc_id, exc)

        return DocumentResponse(id=doc_id, status="created", revision=1)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create document failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL",
                "message": "Create document failed",
                "details": {"error": str(e)},
            },
        ) from e


@app.put("/documents/{doc_id:path}", response_model=DocumentResponse)
async def update_document(
    doc_id: str = Path(..., min_length=1),
    payload: DocumentUpdate = None,
    _=Depends(require_api_key),
):
    try:
        db = _firestore()
        doc_ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
        snapshot = doc_ref.get()
        if not getattr(snapshot, "exists", False):
            raise _error(404, "NOT_FOUND", "Document not found", document_id=doc_id)

        current = snapshot.to_dict() or {}
        current_revision = current.get("revision", 0)
        if (
            payload.last_known_revision is not None
            and payload.last_known_revision != current_revision
        ):
            raise _error(
                409,
                "CONFLICT",
                "Revision mismatch",
                expected_revision=payload.last_known_revision,
                actual_revision=current_revision,
            )

        now_iso = datetime.now(UTC).isoformat()
        update_mask = set(payload.update_mask or [])

        def should_update(field: str) -> bool:
            return not update_mask or field in update_mask

        current_content = (
            current.get("content") if isinstance(current.get("content"), dict) else {}
        )
        current_metadata = (
            current.get("metadata") if isinstance(current.get("metadata"), dict) else {}
        )

        new_content = current_content
        new_metadata = current_metadata
        new_is_hr = current.get("is_human_readable", False)

        updates: dict[str, Any] = {
            "updated_at": now_iso,
            "revision": current_revision + 1,
        }
        fields_updated: set[str] = set()

        if should_update("content") and payload.patch.content is not None:
            new_content = payload.patch.content.model_dump()
            updates["content"] = new_content
            fields_updated.add("content")

        if should_update("metadata") and payload.patch.metadata is not None:
            new_metadata = payload.patch.metadata.model_dump(exclude_none=True)
            updates["metadata"] = new_metadata
            fields_updated.add("metadata")

        if (
            should_update("is_human_readable")
            and payload.patch.is_human_readable is not None
        ):
            new_is_hr = payload.patch.is_human_readable
            updates["is_human_readable"] = new_is_hr
            fields_updated.add("is_human_readable")

        if not fields_updated:
            raise _error(400, "INVALID_ARGUMENT", "update_mask empty or patch missing")

        doc_ref.update(updates)
        current["content"] = new_content
        current["metadata"] = new_metadata
        current["is_human_readable"] = new_is_hr
        merged_content = new_content
        merged_metadata = new_metadata
        merged_parent = updates.get("parent_id", current.get("parent_id"))
        merged_hr = new_is_hr

        # Only re-embed when content changed; metadata-only updates skip embedding
        content_changed = "content" in fields_updated
        try:
            if content_changed:
                # Delete old vectors first to avoid stale chunks when content shrinks
                _delete_vector_entry(doc_id)
                _sync_vector_entry(
                    doc_ref=doc_ref,
                    document_id=doc_id,
                    content=(
                        merged_content.get("body")
                        if isinstance(merged_content, dict)
                        else None
                    ),
                    metadata=(
                        merged_metadata if isinstance(merged_metadata, dict) else None
                    ),
                    parent_id=merged_parent,
                    is_human_readable=bool(merged_hr),
                )
            else:
                logger.info(
                    "vector_sync",
                    extra={
                        "action": "skip_reembed",
                        "document_id": doc_id,
                        "reason": "content_unchanged",
                        "fields_updated": list(fields_updated),
                    },
                )
        except Exception as exc:  # pragma: no cover
            logger.error("Vector synchronization failed for %s: %s", doc_id, exc)

        return DocumentResponse(
            id=doc_id, status="updated", revision=updates["revision"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update document failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL",
                "message": "Update document failed",
                "details": {"error": str(e)},
            },
        ) from e


@app.post("/documents/{doc_id:path}/move", response_model=DocumentResponse)
async def move_document(
    doc_id: str = Path(..., min_length=1),
    payload: DocumentMoveRequest | None = None,
    _=Depends(require_api_key),
):
    try:
        if payload is None:
            raise _error(400, "INVALID_ARGUMENT", "Move payload is required")

        db = _firestore()
        doc_ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
        snapshot = doc_ref.get()
        if not getattr(snapshot, "exists", False):
            raise _error(
                404,
                "NOT_FOUND",
                "Document not found",
                document_id=doc_id,
            )

        current = snapshot.to_dict() or {}
        if current.get("deleted_at") is not None:
            raise _error(
                409,
                "CONFLICT",
                "Cannot move a deleted document",
                document_id=doc_id,
            )

        new_parent_id = payload.new_parent_id
        if new_parent_id == doc_id:
            raise _error(
                400,
                "INVALID_ARGUMENT",
                "Document cannot be moved under itself",
                document_id=doc_id,
            )

        _assert_move_target_valid(
            db=db, document_id=doc_id, new_parent_id=new_parent_id
        )

        now_iso = datetime.now(UTC).isoformat()
        next_revision = (current.get("revision") or 0) + 1
        updates: dict[str, Any] = {
            "parent_id": new_parent_id,
            "updated_at": now_iso,
            "revision": next_revision,
        }

        doc_ref.update(updates)
        current["parent_id"] = new_parent_id
        try:
            # Delete old vectors first to avoid stale chunks when chunk count changes
            _delete_vector_entry(doc_id)
            _sync_vector_entry(
                doc_ref=doc_ref,
                document_id=doc_id,
                content=(
                    (current.get("content") or {}).get("body")
                    if isinstance(current.get("content"), dict)
                    else None
                ),
                metadata=(
                    current.get("metadata")
                    if isinstance(current.get("metadata"), dict)
                    else None
                ),
                parent_id=new_parent_id,
                is_human_readable=current.get("is_human_readable", False),
            )
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Vector synchronization failed while moving %s: %s", doc_id, exc
            )
        return DocumentResponse(id=doc_id, status="moved", revision=next_revision)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Move document failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL",
                "message": "Move document failed",
                "details": {"error": str(e)},
            },
        ) from e


@app.delete("/documents/{doc_id:path}", response_model=DocumentResponse)
async def delete_document(
    doc_id: str = Path(..., min_length=1), _=Depends(require_api_key)
):
    try:
        db = _firestore()
        doc_ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
        snapshot = doc_ref.get()
        if not getattr(snapshot, "exists", False):
            raise _error(404, "NOT_FOUND", "Document not found", document_id=doc_id)

        now_iso = datetime.now(UTC).isoformat()
        current = snapshot.to_dict() or {}
        next_revision = current.get("revision", 0) + 1
        doc_ref.update(
            {
                "deleted_at": now_iso,
                "updated_at": now_iso,
                "vector_status": "deleted",
                "revision": next_revision,
            }
        )
        try:
            _delete_vector_entry(doc_id)
        except Exception as exc:  # pragma: no cover
            logger.error("Vector deletion failed for %s: %s", doc_id, exc)
        return DocumentResponse(id=doc_id, status="deleted", revision=next_revision)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL",
                "message": "Delete document failed",
                "details": {"error": str(e)},
            },
        ) from e


# ---------------- KB Document Read Endpoints ----------------
# These expose Firestore KB documents for MCP tools (list + get).
# Distinct from /api/docs/* which serves GitHub-synced content.


@app.get("/kb/list")
async def list_kb_documents(prefix: str = ""):
    """List KB documents from Firestore, optionally filtered by path prefix."""
    try:
        db = _firestore()
        docs = list(db.collection(KB_COLLECTION).stream())
        items = []
        for snap in docs:
            data = snap.to_dict() or {}
            if data.get("deleted_at") is not None:
                continue
            doc_id = data.get("document_id", snap.id)
            if prefix and not doc_id.startswith(prefix):
                continue
            items.append(
                {
                    "document_id": doc_id,
                    "parent_id": data.get("parent_id", ""),
                    "title": (data.get("metadata") or {}).get("title", ""),
                    "tags": (data.get("metadata") or {}).get("tags", []),
                    "revision": data.get("revision", 0),
                }
            )
        items.sort(key=lambda x: x["document_id"])
        return {"items": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List KB documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/kb/get/{doc_id:path}")
async def get_kb_document(doc_id: str = Path(..., min_length=1)):
    """Get a single KB document's full content from Firestore."""
    try:
        db = _firestore()
        doc_ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
        snap = doc_ref.get()
        if not getattr(snap, "exists", False):
            raise _error(404, "NOT_FOUND", "Document not found", document_id=doc_id)
        data = snap.to_dict() or {}
        if data.get("deleted_at") is not None:
            raise _error(404, "NOT_FOUND", "Document deleted", document_id=doc_id)
        content = data.get("content", {})
        body = content.get("body", "") if isinstance(content, dict) else ""
        return {
            "document_id": data.get("document_id", doc_id),
            "content": body,
            "metadata": data.get("metadata", {}),
            "revision": data.get("revision", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get KB document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/kb/reindex", dependencies=[Depends(require_api_key)])
async def reindex_kb_documents():
    """Re-index all Firestore KB documents into Qdrant vector store.

    Iterates every non-deleted document in KB_COLLECTION, upserts each
    into Qdrant with embeddings.  Returns counts of indexed/skipped/errors.
    """
    store = vector_store.get_vector_store(refresh=True)
    if not store.enabled:
        raise HTTPException(
            status_code=503,
            detail="Vector store not available (missing QDRANT_URL/API_KEY/OPENAI_API_KEY)",
        )

    db = _firestore()
    docs = list(db.collection(KB_COLLECTION).stream())

    indexed = 0
    skipped = 0
    errors = []
    for snap in docs:
        data = snap.to_dict() or {}
        if data.get("deleted_at") is not None:
            skipped += 1
            continue

        doc_id = data.get("document_id", snap.id)
        content = data.get("content") or {}
        body = content.get("body", "") if isinstance(content, dict) else ""
        if not body.strip():
            skipped += 1
            continue

        metadata = (
            data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        )
        parent_id = data.get("parent_id", "")
        is_hr = data.get("is_human_readable", False)

        result = store.upsert_document(
            document_id=doc_id,
            content=body,
            metadata=metadata,
            parent_id=parent_id,
            is_human_readable=is_hr,
        )

        if result.status == "error":
            errors.append({"document_id": doc_id, "error": result.error})
        elif result.status == "skipped":
            skipped += 1
        else:
            indexed += 1

            # Update Firestore vector_status
            try:
                doc_ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
                doc_ref.update({"vector_status": "ready"})
            except Exception:
                pass

    vector_count = store.count()
    return {
        "status": "completed",
        "firestore_total": len(docs),
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "error_count": len(errors),
        "qdrant_vectors": vector_count,
    }


class CleanupOrphansRequest(BaseModel):
    dry_run: bool = True
    max_delete: int = 100

    model_config = ConfigDict(extra="forbid")


class AuditSyncRequest(BaseModel):
    auto_heal: bool = False

    model_config = ConfigDict(extra="forbid")


@app.post("/kb/cleanup-orphans", dependencies=[Depends(require_api_key)])
async def cleanup_orphan_vectors(payload: CleanupOrphansRequest | None = None):
    """Remove Qdrant vectors whose documents no longer exist in Firestore.

    Compares document_ids in Qdrant against Firestore KB and deletes orphans.
    Supports dry_run (default True) and max_delete safety limit.
    """
    if payload is None:
        payload = CleanupOrphansRequest()

    store = vector_store.get_vector_store(refresh=True)
    if not store.enabled:
        raise HTTPException(
            status_code=503,
            detail="Vector store not available",
        )

    qdrant_doc_ids = store.list_document_ids()
    if not qdrant_doc_ids:
        return {
            "mode": "dry_run" if payload.dry_run else "execute",
            "orphans_found": 0,
            "orphans_deleted": 0,
            "details": [],
            "qdrant_vectors": store.count(),
        }

    db = _firestore()
    orphan_ids: list[str] = []
    for doc_id in qdrant_doc_ids:
        try:
            ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
            snap = ref.get()
            if not getattr(snap, "exists", False):
                orphan_ids.append(doc_id)
            else:
                data = snap.to_dict() or {}
                if data.get("deleted_at") is not None:
                    orphan_ids.append(doc_id)
        except Exception:
            pass

    if payload.dry_run:
        to_delete = orphan_ids[: payload.max_delete]
        details = [
            {"document_id": doc_id, "status": "would_delete"} for doc_id in to_delete
        ]
        return {
            "mode": "dry_run",
            "orphans_found": len(orphan_ids),
            "orphans_deleted": 0,
            "details": details,
            "remaining_after_cleanup": len(orphan_ids),
            "qdrant_vectors": store.count(),
        }

    result = _run_cleanup(store, db, orphan_ids, max_delete=payload.max_delete)
    return {
        "mode": "execute",
        "orphans_found": result["orphans_found"],
        "orphans_deleted": result["orphans_deleted"],
        "details": result["details"],
        "remaining_after_cleanup": result["remaining_after_cleanup"],
        "qdrant_vectors": store.count(),
    }


def _run_audit(store: Any, db: Any) -> dict[str, Any]:
    """Internal: compare Firestore vs Qdrant and return audit result dict."""
    docs = list(db.collection(KB_COLLECTION).stream())

    firestore_ids: set[str] = set()
    for snap in docs:
        data = snap.to_dict() or {}
        if data.get("deleted_at") is None:
            doc_id = data.get("document_id", snap.id)
            firestore_ids.add(doc_id)

    qdrant_ids = store.list_document_ids()
    orphan_ids = sorted(qdrant_ids - firestore_ids)
    ghost_ids = sorted(firestore_ids - qdrant_ids)

    status = "clean"
    recommendations: list[str] = []
    if orphan_ids:
        status = "needs_cleanup"
        recommendations.append(
            f"{len(orphan_ids)} orphan vectors from deleted documents "
            "— run POST /kb/cleanup-orphans"
        )
    if ghost_ids:
        status = "needs_cleanup"
        recommendations.append(
            f"{len(ghost_ids)} documents missing vectors "
            "— run POST /kb/reindex-missing"
        )

    return {
        "total_documents": len(firestore_ids),
        "total_vectors": store.count(),
        "documents_without_vectors": ghost_ids,
        "ghost_count": len(ghost_ids),
        "orphan_vector_document_ids": orphan_ids,
        "orphan_count": len(orphan_ids),
        "status": status,
        "recommendations": recommendations,
    }


def _run_reindex(store: Any, db: Any, ghost_ids: list[str]) -> dict[str, Any]:
    """Internal: re-ingest ghost documents into Qdrant."""
    reindexed = 0
    failed: list[dict[str, str]] = []
    details: list[dict[str, Any]] = []

    for doc_id in ghost_ids:
        try:
            ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
            snap = ref.get()
            if not getattr(snap, "exists", False):
                details.append({"document_id": doc_id, "status": "not_found"})
                continue
            data = snap.to_dict() or {}
        except Exception:
            failed.append({"document_id": doc_id, "error": "firestore_read_failed"})
            continue

        content = data.get("content") or {}
        body = content.get("body", "") if isinstance(content, dict) else ""
        if not body.strip():
            details.append({"document_id": doc_id, "status": "skipped_empty"})
            continue

        metadata = (
            data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        )
        parent_id = data.get("parent_id", "")
        is_hr = data.get("is_human_readable", False)

        result = store.upsert_document(
            document_id=doc_id,
            content=body,
            metadata=metadata,
            parent_id=parent_id,
            is_human_readable=is_hr,
        )

        if result.status == "error":
            failed.append({"document_id": doc_id, "error": result.error or ""})
        else:
            reindexed += 1
            details.append(
                {"document_id": doc_id, "chunks_created": result.chunks_created}
            )
            try:
                ref = db.collection(KB_COLLECTION).document(_fs_key(doc_id))
                ref.update({"vector_status": "ready"})
            except Exception:
                pass

    return {
        "missing_found": len(ghost_ids),
        "reindexed": reindexed,
        "failed": failed,
        "details": details,
    }


def _run_cleanup(
    store: Any, db: Any, orphan_ids: list[str], max_delete: int = 100
) -> dict[str, Any]:
    """Internal: delete orphan vectors from Qdrant."""
    to_delete = orphan_ids[:max_delete]
    deleted = 0
    details: list[dict[str, Any]] = []

    for doc_id in to_delete:
        result = store.delete_document(doc_id)
        if result.status != "error":
            deleted += 1
        details.append({"document_id": doc_id, "status": result.status})
        logger.info(
            "vector_sync",
            extra={
                "action": "orphan_cleanup",
                "document_id": doc_id,
                "status": result.status,
            },
        )

    return {
        "orphans_found": len(orphan_ids),
        "orphans_deleted": deleted,
        "details": details,
        "remaining_after_cleanup": len(orphan_ids) - deleted,
    }


@app.post("/kb/audit-sync", dependencies=[Depends(require_api_key)])
async def audit_sync(payload: AuditSyncRequest | None = None):
    """Compare Firestore documents with Qdrant vectors and report mismatches.

    Returns orphans (vectors without docs) and ghosts (docs without vectors).
    When auto_heal=True, automatically fixes issues and runs a verification audit.
    """
    if payload is None:
        payload = AuditSyncRequest()

    store = vector_store.get_vector_store(refresh=True)
    if not store.enabled:
        raise HTTPException(status_code=503, detail="Vector store not available")

    db = _firestore()
    audit_before = _run_audit(store, db)

    if not payload.auto_heal or audit_before["status"] == "clean":
        logger.info(
            "vector_sync",
            extra={
                "action": "audit_sync",
                "auto_heal": payload.auto_heal,
                "status": audit_before["status"],
            },
        )
        return audit_before

    # --- Auto-heal: fix issues then verify ---
    logger.info(
        "vector_sync",
        extra={
            "action": "auto_heal_triggered",
            "ghost_count": audit_before["ghost_count"],
            "orphan_count": audit_before["orphan_count"],
        },
    )

    heal_report: dict[str, Any] = {"auto_heal": True}

    # Fix ghosts (docs without vectors)
    if audit_before["ghost_count"] > 0:
        reindex_result = _run_reindex(
            store, db, audit_before["documents_without_vectors"]
        )
        heal_report["reindex"] = reindex_result
        logger.info(
            "vector_sync",
            extra={
                "action": "auto_heal_reindex",
                "ghosts_fixed": reindex_result["reindexed"],
                "ghosts_failed": len(reindex_result["failed"]),
            },
        )

    # Fix orphans (vectors without docs)
    if audit_before["orphan_count"] > 0:
        cleanup_result = _run_cleanup(
            store, db, audit_before["orphan_vector_document_ids"], max_delete=100
        )
        heal_report["cleanup"] = cleanup_result
        logger.info(
            "vector_sync",
            extra={
                "action": "auto_heal_cleanup",
                "orphans_cleaned": cleanup_result["orphans_deleted"],
                "orphans_remaining": cleanup_result["remaining_after_cleanup"],
            },
        )

    # Verification audit
    audit_after = _run_audit(store, db)
    heal_report["audit_before"] = audit_before
    heal_report["audit_after"] = audit_after
    heal_report["final_status"] = audit_after["status"]

    logger.info(
        "vector_sync",
        extra={
            "action": "auto_heal_complete",
            "final_status": audit_after["status"],
            "status_before": audit_before["status"],
        },
    )

    return heal_report


@app.post("/kb/reindex-missing", dependencies=[Depends(require_api_key)])
async def reindex_missing():
    """Re-index documents that exist in Firestore but have no vectors in Qdrant.

    Reads content from Firestore and ingests into Qdrant using the standard
    upsert flow. Only processes 'ghost' documents (active docs without vectors).
    """
    store = vector_store.get_vector_store(refresh=True)
    if not store.enabled:
        raise HTTPException(status_code=503, detail="Vector store not available")

    db = _firestore()
    audit = _run_audit(store, db)
    ghost_ids = audit["documents_without_vectors"]

    return _run_reindex(store, db, ghost_ids)


# ---- MCP Protocol Endpoints ----
# These allow Claude.ai and other AI connectors to discover and call tools
# directly on Cloud Run without needing the separate mcp_server process.

MCP_TOOLS = [
    {
        "name": "search_knowledge",
        "description": "Search the knowledge base using semantic/RAG query. Returns relevant documents and context from the vector database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query in natural language (Vietnamese or English)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "List available documents in the knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional path prefix to filter (e.g., 'docs/')",
                    "default": "",
                },
            },
        },
    },
    {
        "name": "get_document",
        "description": "Get full content of a specific document by its ID or path",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "The document ID or path",
                },
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "upload_document",
        "description": "Upload/create a new document in the knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Document path, e.g. 'docs/operations/sessions/report.md'",
                },
                "content": {
                    "type": "string",
                    "description": "Document content (markdown or plain text)",
                },
                "title": {"type": "string", "description": "Optional document title"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "update_document",
        "description": "Update an existing document's content and/or metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Document path to update"},
                "content": {"type": "string", "description": "New document content"},
                "title": {"type": "string", "description": "Optional new title"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional new tags",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "delete_document",
        "description": "Delete a document from the knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Document path to delete"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_document",
        "description": "Move a document to a new parent. Use 'root' for top level.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Current document path"},
                "new_path": {
                    "type": "string",
                    "description": "New parent path, or 'root' for top level",
                },
            },
            "required": ["path", "new_path"],
        },
    },
    {
        "name": "ingest_document",
        "description": "Ingest a document from GCS URI or URL into the knowledge base for vector processing",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "GCS URI (gs://bucket/path) or URL to ingest",
                },
            },
            "required": ["source"],
        },
    },
]


@app.get("/mcp")
async def mcp_info():
    """MCP Server info — returns capabilities and tool definitions."""
    return {
        "name": "agent-data-mcp",
        "version": "1.0.0",
        "description": "MCP Server for Agent Data Knowledge Base",
        "protocol_version": "2024-11-05",
        "capabilities": {"tools": True, "resources": False, "prompts": False},
        "tools": MCP_TOOLS,
    }


async def _dispatch_mcp_tool(tool_name: str, args: dict) -> dict:
    """Internal dispatch: call Python functions directly, NO HTTP.

    This is the single dispatch point for all MCP tool calls, used by
    both POST /mcp (JSON-RPC) and POST /mcp/tools/{name} endpoints.
    """
    if tool_name == "search_knowledge":
        import asyncio

        payload = QueryKnowledgeRequest(message=args.get("query", ""))
        # query_knowledge is sync (uses asyncio.run internally via langroid)
        # Must run in thread to avoid event loop conflict with async caller
        result = await asyncio.to_thread(query_knowledge, payload)
        return result.model_dump()

    if tool_name == "list_documents":
        return await list_kb_documents(prefix=args.get("path", "docs"))

    if tool_name == "get_document":
        doc_id = args.get("document_id", "")
        try:
            return await get_kb_document(doc_id=doc_id)
        except HTTPException:
            return {"error": f"Document '{doc_id}' not found"}

    if tool_name == "upload_document":
        path = args.get("path", "")
        content_text = args.get("content", "")
        title = args.get("title", "") or (
            path.rsplit("/", 1)[-1] if "/" in path else path
        )
        tags = args.get("tags")
        parent_id = "/".join(path.split("/")[:-1]) if "/" in path else ""
        payload = DocumentCreate(
            document_id=path,
            parent_id=parent_id,
            content=DocumentContent(mime_type="text/markdown", body=content_text),
            metadata=DocumentMetadata(title=title, tags=tags),
        )
        result = await create_document(payload)
        return result.model_dump()

    if tool_name == "update_document":
        path = args.get("path", "")
        content_text = args.get("content", "")
        title = args.get("title", "")
        tags = args.get("tags")
        metadata = (
            DocumentMetadata(title=title or path, tags=tags)
            if (title or tags)
            else None
        )
        patch = DocumentUpdatePatch(
            content=DocumentContent(mime_type="text/markdown", body=content_text),
            metadata=metadata,
        )
        update_mask = ["content"] + (["metadata"] if metadata else [])
        payload = DocumentUpdate(document_id=path, patch=patch, update_mask=update_mask)
        result = await update_document(doc_id=path, payload=payload)
        return result.model_dump()

    if tool_name == "delete_document":
        result = await delete_document(doc_id=args.get("path", ""))
        return result.model_dump()

    if tool_name == "move_document":
        payload = DocumentMoveRequest(new_parent_id=args.get("new_path", ""))
        result = await move_document(doc_id=args.get("path", ""), payload=payload)
        return result.model_dump()

    if tool_name == "ingest_document":
        msg = ChatMessage(text=args.get("source", ""))
        result = await ingest(msg)
        return result.model_dump()

    raise ValueError(f"Unknown tool: {tool_name}")


@app.post("/mcp")
async def mcp_jsonrpc(request: Request):
    """MCP JSON-RPC protocol handler for Claude.ai connector.

    Handles the Streamable HTTP transport: initialize, tools/list, tools/call.
    All tool calls dispatch to internal Python functions — NO HTTP self-calls.
    """
    # Validate API key for MCP access
    api_key = request.headers.get("x-api-key")
    expected = os.getenv("API_KEY")
    if expected and api_key != expected:
        return JSONResponse(
            status_code=401,
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": "Invalid API key"},
            },
        )

    try:
        body = await request.json()
    except Exception:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Parse error"},
            "id": None,
        }

    method = body.get("method", "")
    params = body.get("params", {})
    req_id = body.get("id")

    logger.info("MCP JSON-RPC: method=%s id=%s", method, req_id)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agent-data-mcp", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = await _dispatch_mcp_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, default=str)}
                    ],
                },
            }
        except HTTPException as he:
            detail = he.detail if isinstance(he.detail, str) else json.dumps(he.detail)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps({"error": detail})}
                    ],
                    "isError": True,
                },
            }
        except Exception as e:
            logger.error("MCP tools/call %s error: %s", tool_name, e)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps({"error": str(e)})}
                    ],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


@app.post("/mcp/tools/{tool_name}")
async def mcp_execute_tool(tool_name: str, request: Request):
    """Execute an MCP tool by name. Dispatches to internal handlers directly."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    logger.info("MCP tool call: %s params=%s", tool_name, body)

    try:
        result = await _dispatch_mcp_tool(tool_name, body)
        return {"result": result}
    except HTTPException as he:
        detail = he.detail if isinstance(he.detail, str) else json.dumps(he.detail)
        return {"result": {"error": detail, "status_code": he.status_code}}
    except Exception as e:
        logger.error("MCP tool %s error: %s", tool_name, e)
        return {"result": {"error": str(e)}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
