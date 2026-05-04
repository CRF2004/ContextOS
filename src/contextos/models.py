"""Data models for ContextOS."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ─── Session ───────────────────────────────────────────────────────────────


class SessionStatus(str, Enum):
    ACTIVE = "active"
    FORKED = "forked"
    ARCHIVED = "archived"


class SessionCreate(BaseModel):
    """Request to create a new session."""

    parent_session_id: str | None = None
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str
    name: str | None
    status: SessionStatus
    parent_session_id: str | None
    total_tokens: int
    created_at: str
    updated_at: str
    metadata: dict[str, Any]


# ─── Token Profiling ───────────────────────────────────────────────────────


class TokenBreakdown(BaseModel):
    """Token usage breakdown for a single request."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    mcp_tokens: int = 0
    skill_tokens: int = 0
    system_tokens: int = 0


class TokenRecord(BaseModel):
    """Persisted token log entry."""

    id: int
    session_id: str
    request_id: str
    timestamp: str
    model: str
    token_breakdown: TokenBreakdown


class TokenSummary(BaseModel):
    """Aggregated token usage for a session."""

    session_id: str
    total_tokens: int = 0
    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_mcp_tokens: int = 0
    total_skill_tokens: int = 0
    total_system_tokens: int = 0


# ─── Message ───────────────────────────────────────────────────────────────


class MessageItem(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class RequestLog(BaseModel):
    """Logged API request."""

    id: int
    session_id: str
    request_id: str
    timestamp: str
    model: str
    messages: list[MessageItem]
    tools: list[dict[str, Any]] | None = None
    system: str | list[dict[str, Any]] | None = None
    token_breakdown: TokenBreakdown
    response_content: str | list[dict[str, Any]] | None = None


# ─── Fork ──────────────────────────────────────────────────────────────────


class ForkRequest(BaseModel):
    session_id: str
    name: str | None = None
    carry_messages: int = Field(default=5, description="Number of recent messages to carry")


class ForkNode(BaseModel):
    """A node in the fork graph."""

    session_id: str
    name: str | None
    parent_session_id: str | None
    fork_point_token: int
    fork_point_time: str
    children: list[str] = Field(default_factory=list)


class ForkGraph(BaseModel):
    """Full fork graph for a session lineage."""

    nodes: list[ForkNode]
    edges: list[tuple[str, str]]  # (parent, child)


# ─── Context Operations ────────────────────────────────────────────────────


class ContextConfig(BaseModel):
    """Configuration for context manipulation."""

    max_prompt_tokens: int = Field(default=180000, description="Max tokens before trimming")
    keep_recent_messages: int = Field(default=10, description="Messages to keep uncompressed")
    max_tools: int = Field(default=20, description="Max tools to include")
    enabled_skills: list[str] = Field(default_factory=list)


class ContextStats(BaseModel):
    """Stats about the current context."""

    total_tokens: int
    message_tokens: int
    tool_tokens: int
    skill_tokens: int
    system_tokens: int
    message_count: int
    tool_count: int
