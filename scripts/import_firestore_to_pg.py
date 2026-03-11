#!/usr/bin/env python3
"""Import Firestore backup JSON into PostgreSQL.

Usage (run on VPS):
    python3 /opt/incomex/docker/agent-data-repo/scripts/import_firestore_to_pg.py

Reads from /opt/incomex/backups/gcp-pre-migration/firestore/*.json
Writes to PostgreSQL incomex_metadata database.

Env vars (from /opt/incomex/docker/.env):
    PG_HOST=postgres (or localhost if running outside Docker)
    PG_PORT=5432
    PG_USER=incomex
    PG_PASSWORD=Incomex2026PG_306ac539ad365fce
    PG_DATABASE=incomex_metadata
"""

import json
import os
import sys

import psycopg2
import psycopg2.extras

BACKUP_DIR = "/opt/incomex/backups/gcp-pre-migration/firestore"


def get_dsn():
    return "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
        user=os.getenv("PG_USER", "incomex"),
        password=os.getenv("PG_PASSWORD", "Incomex2026PG_306ac539ad365fce"),
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DATABASE", "incomex_metadata"),
    )


def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
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
        """)
    conn.commit()
    print("Tables ensured.")


def fs_key(doc_id: str) -> str:
    """Encode document ID same as server.py _fs_key()."""
    return doc_id.replace("/", "__")


def import_kb_documents(conn):
    path = os.path.join(BACKUP_DIR, "kb_documents.json")
    if not os.path.exists(path):
        print(f"SKIP: {path} not found")
        return

    with open(path) as f:
        docs = json.load(f)

    print(f"Importing {len(docs)} kb_documents...")
    imported = 0
    skipped = 0

    with conn.cursor() as cur:
        for doc in docs:
            doc_id = doc.get("document_id", "")
            if not doc_id:
                skipped += 1
                continue

            key = fs_key(doc_id)
            json_data = psycopg2.extras.Json(doc)
            cur.execute(
                """INSERT INTO kb_documents (key, data) VALUES (%s, %s)
                   ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data""",
                (key, json_data),
            )
            imported += 1

    conn.commit()
    print(f"  kb_documents: {imported} imported, {skipped} skipped")


def import_metadata(conn):
    path = os.path.join(BACKUP_DIR, "metadata_test.json")
    if not os.path.exists(path):
        print(f"SKIP: {path} not found")
        return

    with open(path) as f:
        docs = json.load(f)

    print(f"Importing {len(docs)} metadata_test documents...")
    imported = 0

    with conn.cursor() as cur:
        for doc in docs:
            doc_id = doc.get("document_id", doc.get("_id", ""))
            if not doc_id:
                continue
            json_data = psycopg2.extras.Json(doc)
            cur.execute(
                """INSERT INTO metadata_store (key, data) VALUES (%s, %s)
                   ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data""",
                (doc_id, json_data),
            )
            imported += 1

    conn.commit()
    print(f"  metadata_store: {imported} imported")


def verify(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM kb_documents")
        kb_count = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM kb_documents WHERE (data->>'deleted_at') IS NULL"
        )
        kb_active = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM metadata_store")
        meta_count = cur.fetchone()[0]

    print(f"\nVerification:")
    print(f"  kb_documents: {kb_count} total, {kb_active} active")
    print(f"  metadata_store: {meta_count}")


def main():
    dsn = get_dsn()
    print(f"Connecting to PostgreSQL: {dsn.replace(os.getenv('PG_PASSWORD', ''), '***')}")

    conn = psycopg2.connect(dsn)
    conn.autocommit = False

    try:
        ensure_tables(conn)
        conn.autocommit = True
        import_kb_documents(conn)
        import_metadata(conn)
        verify(conn)
        print("\nImport complete!")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
