"""Tests for PostgresChatHistory (via FirestoreChatHistory alias).

Migrated from Firestore fake to pg_store mocks for S109.
"""

from unittest.mock import patch

from agent_data.memory import FirestoreChatHistory


@patch("agent_data.pg_store.clear_chat_messages")
@patch("agent_data.pg_store.get_chat_messages")
@patch("agent_data.pg_store.add_chat_message")
def test_firestore_chat_history_add_get_clear(mock_add, mock_get, mock_clear):
    hist = FirestoreChatHistory("sess-1")

    # add messages
    hist.add_messages({"role": "user", "content": "hello"})
    hist.add_messages({"role": "assistant", "content": "hi there"})
    assert mock_add.call_count == 2

    # get messages
    mock_get.return_value = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    msgs = hist.get_messages()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"

    # clear
    mock_get.return_value = []
    hist.clear()
    mock_clear.assert_called_once_with("sess-1")
    msgs2 = hist.get_messages()
    assert msgs2 == []
