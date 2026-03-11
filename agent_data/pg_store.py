"""PostgreSQL document store — replaces Firestore for metadata persistence.

Migration S109-CP2: All document metadata stored in PostgreSQL using JSONB.
Connection: postgresql://incomex:***@postgres:5432/incomex_metadata

Design: Simple key-value store with JSONB data column, mimicking Firestore's
flat document model. Each "collection" is a separate table.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
import psycopg2.pool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool (module-level singleton)
# ---------------------------------------------------------------------------
_pool: psycopg2.pool.ThreadedConnectionPool | None = None

_TESTING = os.getenv("TESTING") == "1"


def _dsn() -> str:
    """Build DSN from env vars."""
    return os.getenv(
        "PG_DSN",
        "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
            user=os.getenv("PG_USER", "incomex"),
            password=os.getenv("PG_PASSWORD", ""),
            host=os.getenv("PG_HOST", "postgres"),
            port=os.getenv("PG_PORT", "5432"),
            dbname=os.getenv("PG_DATABASE", "incomex_metadata"),
        ),
    )


def init_pool(dsn: str | None = None, minconn: int = 2, maxconn: int = 10) -> None:
    """Initialize the connection pool. Safe to call multiple times."""
    global _pool
    if _pool is not None:
        return
    dsn = dsn or _dsn()
    _pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, dsn)
    logger.info("PostgreSQL pool initialized (min=%d, max=%d)", minconn, maxconn)


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL pool closed")


@contextmanager
def _conn():
    """Get a connection from the pool with auto-commit."""
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized — call init_pool() first")
    conn = _pool.getconn()
    try:
        conn.autocommit = True
        yield conn
    finally:
        _pool.putconn(conn)


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------
def ensure_tables() -> None:
    """Create tables if they don't exist."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS kb_documents (
                    key TEXT PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{}'::jsonb
                );
                CREATE INDEX IF NOT EXISTS idx_kb_documents_doc_id
                    ON kb_documents ((data->>'document_id'));
                CREATE INDEX IF NOT EXISTS idx_kb_documents_deleted
                    ON kb_documents ((data->>'deleted_at'));

                CREATE TABLE IF NOT EXISTS metadata_store (
                    key TEXT PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{}'::jsonb
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    content TEXT NOT NULL DEFAULT '',
                    ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session
                    ON chat_messages (session_id, ts);
            """
            )
    logger.info("PostgreSQL tables ensured")


# ---------------------------------------------------------------------------
# Generic document operations (collection = table name)
# ---------------------------------------------------------------------------
def _table(collection: str) -> str:
    """Map collection name to table. Prevents SQL injection."""
    allowed = {"kb_documents", "metadata_store", "chat_messages"}
    if collection not in allowed:
        raise ValueError(f"Unknown collection: {collection}")
    return collection


def doc_exists(collection: str, key: str) -> bool:
    """Check if a document exists."""
    tbl = _table(collection)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {tbl} WHERE key = %s", (key,))
            return cur.fetchone() is not None


def get_doc(collection: str, key: str) -> dict[str, Any] | None:
    """Get a document by key. Returns the JSONB data dict or None."""
    tbl = _table(collection)
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT data FROM {tbl} WHERE key = %s", (key,))
            row = cur.fetchone()
            return dict(row["data"]) if row else None


def set_doc(collection: str, key: str, data: dict[str, Any]) -> None:
    """Create or replace a document (upsert)."""
    tbl = _table(collection)
    json_data = psycopg2.extras.Json(data)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {tbl} (key, data) VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data""",
                (key, json_data),
            )


def update_doc(collection: str, key: str, updates: dict[str, Any]) -> bool:
    """Merge updates into existing document. Returns False if doc not found."""
    tbl = _table(collection)
    json_updates = psycopg2.extras.Json(updates)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE {tbl} SET data = data || %s WHERE key = %s""",
                (json_updates, key),
            )
            return cur.rowcount > 0


def stream_docs(collection: str) -> list[dict[str, Any]]:
    """Stream all documents in a collection. Returns list of data dicts."""
    tbl = _table(collection)
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT key, data FROM {tbl}")
            return [{"_key": row["key"], **dict(row["data"])} for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Chat message operations (structured table, not JSONB key-value)
# ---------------------------------------------------------------------------
def add_chat_message(session_id: str, role: str, content: str) -> None:
    """Add a chat message to a session."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, role, content),
            )


def get_chat_messages(session_id: str) -> list[dict[str, Any]]:
    """Get all messages for a session, ordered by timestamp."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT role, content, ts FROM chat_messages WHERE session_id = %s ORDER BY ts",
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def clear_chat_messages(session_id: str) -> None:
    """Delete all messages for a session."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_messages WHERE session_id = %s",
                (session_id,),
            )


# ---------------------------------------------------------------------------
# Health probe
# ---------------------------------------------------------------------------
def probe() -> tuple[bool, float]:
    """Quick health check. Returns (ok, latency_ms)."""
    import time

    try:
        t0 = time.monotonic()
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        latency = (time.monotonic() - t0) * 1000
        return True, latency
    except Exception:
        return False, 0.0
