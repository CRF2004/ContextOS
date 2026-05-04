"""Tests for ContextOS session store."""

import pytest

from contextos.models import (
    ContextConfig,
    MessageItem,
    SessionCreate,
    TokenBreakdown,
)
from contextos.session_store import SessionStore


@pytest.fixture
def store(tmp_path):
    s = SessionStore(db_path=str(tmp_path / "test.db"))
    return s


@pytest.mark.asyncio
async def test_create_and_get_session(store):
    await store.connect()
    try:
        session = await store.create_session(SessionCreate(name="test"))
        assert session.name == "test"
        assert session.status.value == "active"
        assert session.total_tokens == 0

        retrieved = await store.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_list_sessions(store):
    await store.connect()
    try:
        await store.create_session(SessionCreate(name="s1"))
        await store.create_session(SessionCreate(name="s2"))

        sessions = await store.list_sessions()
        assert len(sessions) == 2
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_token_recording(store):
    await store.connect()
    try:
        session = await store.create_session(SessionCreate(name="test"))

        breakdown = TokenBreakdown(
            total_tokens=200,
            prompt_tokens=150,
            completion_tokens=50,
            mcp_tokens=30,
            skill_tokens=0,
            system_tokens=20,
        )

        await store.save_token_record(session.session_id, "req_1", "claude-3-5-sonnet", breakdown)

        summary = await store.get_token_summary(session.session_id)
        assert summary.total_tokens == 200
        assert summary.total_requests == 1
        assert summary.total_prompt_tokens == 150
        assert summary.total_completion_tokens == 50
        assert summary.total_mcp_tokens == 30
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_request_logging(store):
    await store.connect()
    try:
        session = await store.create_session(SessionCreate(name="test"))

        breakdown = TokenBreakdown(total_tokens=100, prompt_tokens=80, completion_tokens=20)
        messages = [MessageItem(role="user", content="Hello")]

        await store.save_request_log(
            session.session_id,
            "req_1",
            "claude-3-5-sonnet",
            messages,
            breakdown,
            response_content="Hi!",
        )

        logs = await store.get_request_logs(session.session_id)
        assert len(logs) == 1
        assert logs[0].request_id == "req_1"
        assert len(logs[0].messages) == 1
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_session_fork_graph(store):
    await store.connect()
    try:
        parent = await store.create_session(SessionCreate(name="parent"))
        child = await store.create_session(
            SessionCreate(name="child", parent_session_id=parent.session_id)
        )

        graph = await store.get_fork_graph(parent.session_id)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_archive_session(store):
    await store.connect()
    try:
        session = await store.create_session(SessionCreate(name="test"))
        await store.archive_session(session.session_id)

        retrieved = await store.get_session(session.session_id)
        assert retrieved.status.value == "archived"
    finally:
        await store.close()
