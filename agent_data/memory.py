"""PostgreSQL-backed chat history backend.

Migration S109-CP2: Replaced Firestore with PostgreSQL for chat persistence.
Uses pg_store module for all database operations.
"""

from collections.abc import Mapping, MutableMapping
from typing import Any

try:  # Prefer real Langroid ChatHistory when available
    from langroid.agent.chat_history import ChatHistory  # type: ignore
except Exception:  # Fallback stub to avoid hard dependency at import time

    class ChatHistory:  # type: ignore
        def __init__(self) -> None:
            pass


class PostgresChatHistory(ChatHistory):
    """PostgreSQL-backed implementation of Langroid's ChatHistory.

    Provides minimal persistence for chat messages per session.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id

    def add_messages(self, messages):  # type: ignore[override]
        """Add one or more messages to the session history."""
        from agent_data import pg_store

        if not isinstance(messages, list | tuple):
            messages = [messages]

        for msg in messages:
            data = self._serialize_message(msg)
            pg_store.add_chat_message(
                session_id=self.session_id,
                role=data["role"],
                content=data["content"],
            )

    def get_messages(self):  # type: ignore[override]
        """Retrieve messages for the current session."""
        from agent_data import pg_store

        rows = pg_store.get_chat_messages(self.session_id)
        return [self._deserialize_message(row) for row in rows]

    def clear(self):  # type: ignore[override]
        """Delete all messages for the current session."""
        from agent_data import pg_store

        pg_store.clear_chat_messages(self.session_id)

    @staticmethod
    def _serialize_message(msg: Any) -> MutableMapping[str, Any]:
        if isinstance(msg, Mapping):
            role = msg.get("role", "user")
            content = msg.get("content", "")
        else:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
        return {"role": role, "content": content}

    @staticmethod
    def _deserialize_message(data: Mapping[str, Any]) -> MutableMapping[str, Any]:
        out: MutableMapping[str, Any] = {
            "role": data.get("role", "user"),
            "content": data.get("content", ""),
        }
        if "ts" in data:
            out["ts"] = data["ts"]
        return out


# Backward-compatible alias
FirestoreChatHistory = PostgresChatHistory
