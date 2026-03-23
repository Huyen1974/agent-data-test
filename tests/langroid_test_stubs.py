"""Offline langroid stubs for unit tests.

Avoids importing the real langroid package during selected offline tests, which
would otherwise trigger tokenizer downloads outside the sandbox.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass


def install_langroid_stubs() -> None:
    if "langroid" in sys.modules:
        return

    langroid = types.ModuleType("langroid")
    agent_mod = types.ModuleType("langroid.agent")
    special_mod = types.ModuleType("langroid.agent.special")
    doc_chat_mod = types.ModuleType("langroid.agent.special.doc_chat_agent")
    tool_message_mod = types.ModuleType("langroid.agent.tool_message")
    chat_agent_mod = types.ModuleType("langroid.agent.chat_agent")
    chat_history_mod = types.ModuleType("langroid.agent.chat_history")
    language_models_mod = types.ModuleType("langroid.language_models")
    vector_store_mod = types.ModuleType("langroid.vector_store")
    qdrantdb_mod = types.ModuleType("langroid.vector_store.qdrantdb")

    class ChatAgent:
        pass

    class Task:
        pass

    class OpenAIGPTConfig:
        pass

    class ChatHistory:
        def __init__(self) -> None:
            pass

    @dataclass
    class DocChatAgentConfig:
        vecdb: object | None = None
        doc_paths: list[str] | None = None

        def __post_init__(self) -> None:
            if self.doc_paths is None:
                self.doc_paths = []

    class DocChatAgent:
        def __init__(self, config: DocChatAgentConfig | None = None) -> None:
            self.config = config or DocChatAgentConfig()
            self.vecdb = getattr(self.config, "vecdb", None)
            self.tools: list[str] = []

        def ingest_doc_paths(self, *args, **kwargs):
            return "stub-ingest"

        def clear_history(self, *args, **kwargs) -> None:
            return None

        def clear_dialog(self) -> None:
            return None

        def llm_response(self, text: str):
            return types.SimpleNamespace(content=text)

    def tool(func=None, *args, **kwargs):  # type: ignore[override]
        def _wrap(f):
            return f

        return _wrap(func) if callable(func) else _wrap

    @dataclass
    class QdrantDBConfig:
        collection_name: str = "test_documents"
        cloud: bool = True

    class ToolMessage:
        pass

    langroid.ChatAgent = ChatAgent
    langroid.Task = Task
    agent_mod.ChatAgent = ChatAgent
    agent_mod.Task = Task
    doc_chat_mod.DocChatAgent = DocChatAgent
    doc_chat_mod.DocChatAgentConfig = DocChatAgentConfig
    tool_message_mod.ToolMessage = ToolMessage
    chat_agent_mod.tool = tool
    chat_history_mod.ChatHistory = ChatHistory
    language_models_mod.OpenAIGPTConfig = OpenAIGPTConfig
    qdrantdb_mod.QdrantDBConfig = QdrantDBConfig

    sys.modules["langroid"] = langroid
    sys.modules["langroid.agent"] = agent_mod
    sys.modules["langroid.agent.special"] = special_mod
    sys.modules["langroid.agent.special.doc_chat_agent"] = doc_chat_mod
    sys.modules["langroid.agent.tool_message"] = tool_message_mod
    sys.modules["langroid.agent.chat_agent"] = chat_agent_mod
    sys.modules["langroid.agent.chat_history"] = chat_history_mod
    sys.modules["langroid.language_models"] = language_models_mod
    sys.modules["langroid.vector_store"] = vector_store_mod
    sys.modules["langroid.vector_store.qdrantdb"] = qdrantdb_mod

    if "psycopg2" not in sys.modules:
        psycopg2_mod = types.ModuleType("psycopg2")
        extras_mod = types.ModuleType("psycopg2.extras")
        pool_mod = types.ModuleType("psycopg2.pool")

        class ThreadedConnectionPool:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def getconn(self):
                raise RuntimeError(
                    "psycopg2 pool stub should not be used in offline tests"
                )

            def putconn(self, conn) -> None:
                return None

            def closeall(self) -> None:
                return None

        class RealDictCursor:
            pass

        def Json(data):
            return data

        psycopg2_mod.extras = extras_mod
        psycopg2_mod.pool = pool_mod
        extras_mod.RealDictCursor = RealDictCursor
        extras_mod.Json = Json
        pool_mod.ThreadedConnectionPool = ThreadedConnectionPool

        sys.modules["psycopg2"] = psycopg2_mod
        sys.modules["psycopg2.extras"] = extras_mod
        sys.modules["psycopg2.pool"] = pool_mod
