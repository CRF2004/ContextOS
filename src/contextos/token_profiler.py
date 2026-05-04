"""Token profiling for Claude API requests and responses."""

from __future__ import annotations

import logging
from typing import Any

import tiktoken

from .models import TokenBreakdown

logger = logging.getLogger(__name__)

# Model prefix → encoding name mapping
_MODEL_ENCODING = {
    "claude-sonnet-4-20250514": "claude-3-5-sonnet-20241022",
    "claude-sonnet": "claude-3-5-sonnet-20241022",
    "claude-opus-4-20250514": "claude-3-opus-20240229",
    "claude-opus": "claude-3-opus-20240229",
    "claude-haiku": "claude-3-haiku-20240307",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku": "claude-3-haiku-20240307",
}

_CACHED_ENCODERS: dict[str, Any] = {}


def _get_encoding(model: str) -> Any:
    """Get tiktoken encoding for a Claude model."""
    if model in _CACHED_ENCODERS:
        return _CACHED_ENCODERS[model]

    enc_name = None
    for prefix, enc in _MODEL_ENCODING.items():
        if model.startswith(prefix):
            enc_name = enc
            break

    if enc_name is None:
        # Default to claude-3-5-sonnet encoding
        enc_name = "claude-3-5-sonnet-20241022"
        logger.warning(f"Unknown model '{model}', falling back to {enc_name} encoding")

    try:
        enc = tiktoken.get_encoding(enc_name)
    except Exception:
        # Final fallback
        enc = tiktoken.get_encoding("cl100k_base")

    _CACHED_ENCODERS[model] = enc
    return enc


def count_tokens(text: str, model: str = "claude-3-5-sonnet-20241022") -> int:
    """Count tokens in a text string."""
    if not text:
        return 0
    enc = _get_encoding(model)
    return len(enc.encode(text))


def count_message_tokens(messages: list[dict[str, Any]], model: str = "claude-3-5-sonnet-20241022") -> int:
    """Count tokens for a list of messages."""
    total = 0
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        # Role overhead (~4 tokens per message)
        total += 4
        if isinstance(content, str):
            total += count_tokens(content, model)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        total += count_tokens(block.get("text", ""), model)
                    elif block.get("type") == "tool_result":
                        total += count_tokens(str(block.get("content", "")), model)
    return total


def count_tool_tokens(tools: list[dict[str, Any]], model: str = "claude-3-5-sonnet-20241022") -> int:
    """Count tokens consumed by tool definitions in the system prompt."""
    total = 0
    for tool in tools:
        # Tool name
        total += count_tokens(tool.get("name", ""), model)
        # Tool description
        total += count_tokens(tool.get("description", ""), model)
        # Input schema
        schema = tool.get("input_schema", {})
        total += count_tokens(str(schema), model)
    return total


def count_system_tokens(system: str | list[dict[str, Any]], model: str = "claude-3-5-sonnet-20241022") -> int:
    """Count tokens in the system prompt."""
    if system is None:
        return 0
    if isinstance(system, str):
        return count_tokens(system, model)
    if isinstance(system, list):
        total = 0
        for block in system:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    total += count_tokens(block.get("text", ""), model)
        return total
    return 0


def profile_request(
    messages: list[dict[str, Any]],
    model: str,
    tools: list[dict[str, Any]] | None = None,
    system: str | list[dict[str, Any]] | None = None,
) -> TokenBreakdown:
    """Profile token usage for an outgoing request."""
    system_tokens = count_system_tokens(system, model)
    message_tokens = count_message_tokens(messages, model)
    tool_tokens = count_tool_tokens(tools or [], model) if tools else 0

    # skill_tokens: portion of system prompt from injected skills
    # For now, we treat the entire system prompt as skill tokens if no other info
    # This can be refined later with skill tagging
    return TokenBreakdown(
        prompt_tokens=system_tokens + message_tokens + tool_tokens,
        system_tokens=system_tokens,
        mcp_tokens=tool_tokens,
        skill_tokens=0,  # Will be set by context engine
    )


def profile_response(
    response: dict[str, Any],
    model: str = "claude-3-5-sonnet-20241022",
) -> TokenBreakdown:
    """Profile token usage from an API response."""
    usage = response.get("usage", {})
    completion_tokens = usage.get("output_tokens", 0)
    prompt_tokens = usage.get("input_tokens", 0)

    # Try to extract MCP tool tokens from response content
    mcp_tokens = 0
    skill_tokens = 0
    system_tokens = 0

    content = response.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                # Tool use blocks in response consume completion tokens
                name = block.get("name", "")
                input_data = block.get("input", {})
                mcp_tokens += count_tokens(name, model) + count_tokens(str(input_data), model)

    return TokenBreakdown(
        total_tokens=prompt_tokens + completion_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        mcp_tokens=mcp_tokens,
        skill_tokens=skill_tokens,
        system_tokens=0,
    )
