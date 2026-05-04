"""Tests for ContextOS context engine."""

import pytest

from contextos.context_engine import ContextEngine
from contextos.models import ContextConfig


def test_get_stats():
    engine = ContextEngine()
    messages = [
        {"role": "user", "content": "Hello world"},
        {"role": "assistant", "content": "Hi there"},
    ]
    stats = engine.get_stats(messages, "claude-3-5-sonnet-20241022")
    assert stats.total_tokens > 0
    assert stats.message_count == 2


def test_needs_trimming_no():
    engine = ContextEngine()
    messages = [{"role": "user", "content": "short"}]
    assert not engine.needs_trimming(messages, "claude-3-5-sonnet-20241022")


def test_trim_messages_keeps_recent():
    engine = ContextEngine(config=ContextConfig(keep_recent_messages=3))
    messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(10)]
    trimmed = engine.trim_messages(messages, "claude-3-5-sonnet-20241022")
    # Without exceeding budget, should return all
    assert len(trimmed) == 10


def test_trim_messages_with_summary():
    engine = ContextEngine(config=ContextConfig(keep_recent_messages=3))
    # Simulate a long context that exceeds budget by using a very low max
    engine.config.max_prompt_tokens = 50
    messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"This is message number {i} with extra text"} for i in range(20)]
    trimmed = engine.trim_messages(messages, "claude-3-5-sonnet-20241022", summary="Summary of conversation")
    # Should have summary + 3 recent messages
    assert len(trimmed) == 4


def test_prune_tools():
    engine = ContextEngine(config=ContextConfig(max_tools=3))
    tools = [{"name": f"tool_{i}", "description": f"Tool {i}"} for i in range(5)]
    pruned = engine.prune_tools(tools, "claude-3-5-sonnet-20241022")
    assert len(pruned) == 3


def test_inject_skill_string():
    engine = ContextEngine()
    result = engine.inject_skill("You are helpful.", "Skill prompt here")
    assert "Skill prompt here" in result
    assert "You are helpful." in result


def test_inject_skill_none():
    engine = ContextEngine()
    result = engine.inject_skill(None, "Skill prompt")
    assert result == {"type": "text", "text": "Skill prompt"}


def test_inject_skill_list():
    engine = ContextEngine()
    result = engine.inject_skill([{"type": "text", "text": "System"}], "Skill")
    assert len(result) == 2


def test_apply_context_config():
    engine = ContextEngine(config=ContextConfig(max_tools=2))
    messages = [{"role": "user", "content": "Hello"}]
    tools = [{"name": f"t_{i}"} for i in range(5)]
    result_msgs, result_tools, _ = engine.apply_context_config(messages, tools, None, "claude-3-5-sonnet-20241022")
    assert len(result_tools) == 2
