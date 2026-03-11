"""
AgentData core classes.

This module introduces the foundational AgentData class and its configuration
as the base for a future Knowledge Manager. It subclasses Langroid's
DocChatAgent and DocChatAgentConfig to stay aligned with existing agent
capabilities while remaining easy to extend.

References:
- Plan V12: ID 1.1 — Create AgentData Core Class
- Reuse Plan A1 — Foundational module for future reuse and extension
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from agent_data.memory import PostgresChatHistory

from langroid.agent.special.doc_chat_agent import (
    DocChatAgent,
    DocChatAgentConfig,
)
from langroid.agent.tool_message import ToolMessage  # noqa: F401

try:  # prefer canonical location
    from langroid.agent.chat_agent import tool  # type: ignore
except Exception:  # pragma: no cover - compatibility shim for older Langroid

    def tool(func=None, *args, **kwargs):  # type: ignore
        def _wrap(f):
            return f

        return _wrap(func) if callable(func) else _wrap


__all__ = ["AgentDataConfig", "AgentData"]


class AgentDataConfig(DocChatAgentConfig):
    """Configuration for the AgentData agent.

    Currently identical to ``DocChatAgentConfig`` and serves as a placeholder
    for future, AgentData-specific options.

    - Plan V12 ID 1.1
    - Reuse Plan A1
    """


class AgentData(DocChatAgent):
    """AgentData: the core agent for the Knowledge Manager.

    This class extends Langroid's ``DocChatAgent`` and is intended to be the
    foundation for higher-level orchestration and capabilities. It is designed
    for straightforward future extension with AgentData-specific behaviors.

    - Plan V12 ID 1.1
    - Reuse Plan A1
    """

    # PostgreSQL collection to store document metadata
    METADATA_COLLECTION = "metadata_store"

    def __init__(self, config: AgentDataConfig) -> None:
        super().__init__(config)

        # Load optional system prompts from prompts/ repository
        self.system_prompt: str | None = None
        self.summarization_prompt: str | None = None

        try:
            project_root = Path(__file__).resolve().parents[1]
            prompts_dir = project_root / "prompts"
            if prompts_dir.is_dir():
                rag_path = prompts_dir / "rag_system_prompt.md"
                if rag_path.exists():
                    self.system_prompt = rag_path.read_text(encoding="utf-8").strip()
                sum_path = prompts_dir / "summarization_prompt.md"
                if sum_path.exists():
                    self.summarization_prompt = sum_path.read_text(
                        encoding="utf-8"
                    ).strip()
        except Exception:
            # Non-fatal: continue without prompts if not present
            self.system_prompt = self.system_prompt or None
            self.summarization_prompt = self.summarization_prompt or None

        # PostgreSQL-backed: db flag indicates store availability
        self.db = None
        try:
            from agent_data import pg_store

            pg_store.init_pool()
            pg_store.ensure_tables()
            self.db = True  # Flag: PostgreSQL is available
        except Exception:
            self.db = None

        # Integrate PostgreSQL-backed chat history (initialize default session)
        self.history = None
        try:
            self.history = PostgresChatHistory(session_id="default")
        except Exception:
            self.history = None

        # Track tool registrations for simple verification/tests.
        self.tools = getattr(self, "tools", []) or []
        if "gcs_ingest" not in self.tools:
            self.tools.append("gcs_ingest")
        # Keep a simple preview/cache of last ingested text content (for demo/tests)
        self.last_ingested_text: str | None = None

    def ingest(self) -> None:
        """Override to skip noisy warnings when vecdb is unavailable."""
        try:
            if len(self.config.doc_paths) == 0 and self.vecdb is None:
                return
        except Exception:
            pass
        super().ingest()

    # -------- Session helpers --------
    def set_session(self, session_id: str) -> None:
        """Bind this agent to a session-backed chat history."""
        try:
            if self.db is not None:
                self.history = PostgresChatHistory(session_id=session_id)
            else:
                self.history = None
        except Exception:
            self.history = None

    def ingest_doc_paths(self, paths, *args, **kwargs) -> str:
        """Overrides the parent method to automatically persist metadata after ingestion."""

        # Execute the standard ingestion (vector store, parsing, etc.)
        try:
            parent_result = super().ingest_doc_paths(paths, *args, **kwargs)
        except Exception as e:
            parent_result = f"Ingestion skipped or failed: {e}"

        if isinstance(paths, str | bytes):
            norm_paths = [paths]
        else:
            norm_paths = list(paths)

        saved_ids: list[str] = []
        errors: list[str] = []

        for p in norm_paths:
            if isinstance(p, bytes):
                continue
            try:
                doc_id = Path(p).name
                initial_metadata = {
                    "source_uri": p,
                    "ingestion_status": "completed",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                }
                _ = self.add_metadata(doc_id, json.dumps(initial_metadata))
                saved_ids.append(doc_id)
            except Exception as e:  # pragma: no cover
                errors.append(f"{p}: {e}")

        meta_note = (
            f"metadata saved for {len(saved_ids)} doc(s): {', '.join(saved_ids)}"
            if saved_ids
            else "no metadata saved"
        )
        if errors:
            meta_note += f"; {len(errors)} error(s) during metadata save"

        return f"Ingestion complete. Result: {parent_result}. Metadata: {meta_note}."

    @tool
    def gcs_ingest(self, gcs_uri: str) -> str:
        """GCS ingestion is disabled after S109 migration to VPS.

        Returns a message indicating GCS is no longer supported.
        Inline text ingestion via /ingest endpoint still works.
        """
        return (
            "GCS ingestion is disabled. The system no longer depends on Google Cloud Storage. "
            f"Use inline text ingestion via POST /ingest instead. URI: {gcs_uri}"
        )

    @tool
    def add_metadata(self, document_id: str, metadata_json: str) -> str:
        """Adds or overwrites metadata for a given document ID in PostgreSQL."""

        if "add_metadata" not in self.tools:
            self.tools.append("add_metadata")

        if self.db is None:
            return "PostgreSQL store not initialized."
        try:
            data = json.loads(metadata_json)
        except Exception as e:  # pragma: no cover
            return f"Invalid metadata JSON: {e}"

        try:
            from agent_data import pg_store

            pg_store.set_doc(self.METADATA_COLLECTION, document_id, data)
            return f"Metadata for {document_id} saved."
        except Exception as e:  # pragma: no cover
            return f"Failed to add metadata for {document_id}: {e}"

    @tool
    def get_metadata(self, document_id: str) -> str:
        """Retrieves the metadata for a given document ID from PostgreSQL."""

        if "get_metadata" not in self.tools:
            self.tools.append("get_metadata")

        if self.db is None:
            return "PostgreSQL store not initialized."
        try:
            from agent_data import pg_store

            data = pg_store.get_doc(self.METADATA_COLLECTION, document_id)
            if data is not None:
                try:
                    return json.dumps(data)
                except Exception:
                    return str(data)
            else:
                return f"Metadata not found for {document_id}."
        except Exception as e:  # pragma: no cover
            return f"Failed to get metadata for {document_id}: {e}"

    @tool
    def update_ingestion_status(self, document_id: str, status: str) -> str:
        """Updates the ingestion status for a document in PostgreSQL."""

        if "update_ingestion_status" not in self.tools:
            self.tools.append("update_ingestion_status")

        if self.db is None:
            return "PostgreSQL store not initialized."
        try:
            from agent_data import pg_store

            pg_store.update_doc(
                self.METADATA_COLLECTION, document_id, {"ingestion_status": status}
            )
            return f"Ingestion status for {document_id} updated to '{status}'."
        except Exception as e:  # pragma: no cover
            return f"Failed to update status for {document_id}: {e}"
