"""Tests for ContextOS token profiler."""

import pytest

from contextos.token_profiler import (
    count_message_tokens,
    count_system_tokens,
    count_tokens,
    count_tool_tokens,
    profile_request,
    profile_response,
)


def test_count_tokens_basic():
    assert count_tokens("") == 0
    assert count_tokens("Hello") > 0


def test_count_tokens_long_text():
    text = " ".join(["word"] * 1000)
    assert count_tokens(text) > 100


def test_count_message_tokens():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    tokens = count_message_tokens(messages)
    assert tokens > 0


def test_count_message_tokens_complex_content():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image"},
            ],
        },
    ]
    tokens = count_message_tokens(messages)
    assert tokens > 0


def test_count_system_tokens_str():
    tokens = count_system_tokens("You are a helpful assistant.")
    assert tokens > 0


def test_count_system_tokens_list():
    system = [{"type": "text", "text": "System prompt here"}]
    tokens = count_system_tokens(system)
    assert tokens > 0


def test_count_system_tokens_none():
    assert count_system_tokens(None) == 0


def test_count_tool_tokens():
    tools = [
        {
            "name": "search",
            "description": "Search the web",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }
    ]
    tokens = count_tool_tokens(tools)
    assert tokens > 0


def test_count_tool_tokens_empty():
    assert count_tool_tokens([]) == 0


def test_profile_request():
    messages = [{"role": "user", "content": "What is the weather?"}]
    result = profile_request(messages, "claude-3-5-sonnet-20241022")
    assert result.prompt_tokens > 0
    assert result.completion_tokens == 0
    assert result.total_tokens == 0  # Only prompt side, no response yet


def test_profile_response():
    response = {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "The weather is sunny."}],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    result = profile_response(response)
    assert result.total_tokens == 150
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50
