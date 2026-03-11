"""Tests for PostgresChatHistory (formerly FirestoreChatHistory)."""

from unittest.mock import patch

import pytest

from agent_data.memory import FirestoreChatHistory, PostgresChatHistory

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


def test_backward_compat_alias():
    assert FirestoreChatHistory is PostgresChatHistory


def test_init_sets_attributes_and_calls_super():
    with patch(
        "agent_data.memory.ChatHistory.__init__", return_value=None
    ) as super_init:
        inst = PostgresChatHistory(session_id="session-123")
        super_init.assert_called_once()

    assert inst.session_id == "session-123"


@patch("agent_data.pg_store.add_chat_message")
def test_add_messages_single_dict(mock_add):
    inst = PostgresChatHistory(session_id="s")
    inst.add_messages({"role": "user", "content": "hi"})
    mock_add.assert_called_once_with(session_id="s", role="user", content="hi")


@patch("agent_data.pg_store.add_chat_message")
def test_add_messages_list(mock_add):
    inst = PostgresChatHistory(session_id="s")
    inst.add_messages(
        [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
    )
    assert mock_add.call_count == 2


@patch("agent_data.pg_store.get_chat_messages")
def test_get_messages(mock_get):
    mock_get.return_value = [
        {"role": "user", "content": "a", "ts": 1},
        {"role": "assistant", "content": "b", "ts": 2},
    ]
    inst = PostgresChatHistory(session_id="s")
    msgs = inst.get_messages()
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "user" and msgs[0]["content"] == "a"
    mock_get.assert_called_once_with("s")


@patch("agent_data.pg_store.clear_chat_messages")
def test_clear(mock_clear):
    inst = PostgresChatHistory(session_id="s")
    inst.clear()
    mock_clear.assert_called_once_with("s")
