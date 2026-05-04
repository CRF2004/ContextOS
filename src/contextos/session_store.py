"""SQLite-based session store for ContextOS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from .models import (
    ForkGraph,
    ForkNode,
    MessageItem,
    RequestLog,
    SessionCreate,
    SessionResponse,
    SessionStatus,
    TokenBreakdown,
    TokenRecord,
    TokenSummary,
)

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    parent_session_id TEXT,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS token_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    mcp_tokens INTEGER NOT NULL DEFAULT 0,
    skill_tokens INTEGER NOT NULL DEFAULT 0,
    system_tokens INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    messages TEXT NOT NULL DEFAULT '[]',
    tools TEXT,
    system TEXT,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    mcp_tokens INTEGER NOT NULL DEFAULT 0,
    skill_tokens INTEGER NOT NULL DEFAULT 0,
    system_tokens INTEGER NOT NULL DEFAULT 0,
    response_content TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_token_session ON token_records(session_id);
CREATE INDEX IF NOT EXISTS idx_request_session ON request_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_request_time ON request_logs(timestamp);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: str | None) -> Any:
    if s is None:
        return None
    return json.loads(s)


class SessionStore:
    """SQLite-backed session, token, and request store."""

    def __init__(self, db_path: str = "./contextos.db"):
        self.db_path = db_path
        self._db: aiosqlite.AIOSqlite | None = None

    async def connect(self) -> None:
        db_dir = str(Path(self.db_path).parent)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(DB_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.AIOSqlite:
        if self._db is None:
            raise RuntimeError("SessionStore not connected. Call connect() first.")
        return self._db

    # ─── Sessions ────────────────────────────────────────────────────

    async def create_session(self, req: SessionCreate) -> SessionResponse:
        import uuid
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        await self.db.execute(
            """INSERT INTO sessions (session_id, name, status, parent_session_id, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                req.name,
                SessionStatus.ACTIVE.value,
                req.parent_session_id,
                _json_dumps(req.metadata),
                now,
                now,
            ),
        )
        await self.db.commit()
        return SessionResponse(
            session_id=session_id,
            name=req.name,
            status=SessionStatus.ACTIVE,
            parent_session_id=req.parent_session_id,
            total_tokens=0,
            created_at=now,
            updated_at=now,
            metadata=req.metadata,
        )

    async def get_session(self, session_id: str) -> SessionResponse | None:
        row = await self.db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = await row.fetchone()
        if row is None:
            return None
        return SessionResponse(
            session_id=row["session_id"],
            name=row["name"],
            status=SessionStatus(row["status"]),
            parent_session_id=row["parent_session_id"],
            total_tokens=row["total_tokens"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=_json_loads(row["metadata"]),
        )

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionResponse]:
        rows = await self.db.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await rows.fetchall()
        return [
            SessionResponse(
                session_id=r["session_id"],
                name=r["name"],
                status=SessionStatus(r["status"]),
                parent_session_id=r["parent_session_id"],
                total_tokens=r["total_tokens"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                metadata=_json_loads(r["metadata"]),
            )
            for r in rows
        ]

    async def update_session_tokens(self, session_id: str, tokens: int) -> None:
        await self.db.execute(
            "UPDATE sessions SET total_tokens = total_tokens + ?, updated_at = ? WHERE session_id = ?",
            (tokens, _now_iso(), session_id),
        )
        await self.db.commit()

    async def archive_session(self, session_id: str) -> None:
        await self.db.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
            (SessionStatus.ARCHIVED.value, _now_iso(), session_id),
        )
        await self.db.commit()

    # ─── Token Records ───────────────────────────────────────────────

    async def save_token_record(
        self, session_id: str, request_id: str, model: str, breakdown: TokenBreakdown
    ) -> None:
        await self.db.execute(
            """INSERT INTO token_records
               (session_id, request_id, timestamp, model, total_tokens, prompt_tokens,
                completion_tokens, mcp_tokens, skill_tokens, system_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                request_id,
                _now_iso(),
                model,
                breakdown.total_tokens,
                breakdown.prompt_tokens,
                breakdown.completion_tokens,
                breakdown.mcp_tokens,
                breakdown.skill_tokens,
                breakdown.system_tokens,
            ),
        )
        await self.db.commit()
        await self.update_session_tokens(session_id, breakdown.total_tokens)

    async def get_token_summary(self, session_id: str) -> TokenSummary:
        row = await self.db.execute(
            """SELECT COUNT(*) as cnt,
                      COALESCE(SUM(total_tokens), 0) as total,
                      COALESCE(SUM(prompt_tokens), 0) as prompt,
                      COALESCE(SUM(completion_tokens), 0) as completion,
                      COALESCE(SUM(mcp_tokens), 0) as mcp,
                      COALESCE(SUM(skill_tokens), 0) as skill,
                      COALESCE(SUM(system_tokens), 0) as system
               FROM token_records WHERE session_id = ?""",
            (session_id,),
        )
        row = await row.fetchone()
        return TokenSummary(
            session_id=session_id,
            total_tokens=row["total"],
            total_requests=row["cnt"],
            total_prompt_tokens=row["prompt"],
            total_completion_tokens=row["completion"],
            total_mcp_tokens=row["mcp"],
            total_skill_tokens=row["skill"],
            total_system_tokens=row["system"],
        )

    async def get_token_history(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> list[TokenRecord]:
        rows = await self.db.execute(
            """SELECT * FROM token_records WHERE session_id = ?
               ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
            (session_id, limit, offset),
        )
        rows = await rows.fetchall()
        return [
            TokenRecord(
                id=r["id"],
                session_id=r["session_id"],
                request_id=r["request_id"],
                timestamp=r["timestamp"],
                model=r["model"],
                token_breakdown=TokenBreakdown(
                    total_tokens=r["total_tokens"],
                    prompt_tokens=r["prompt_tokens"],
                    completion_tokens=r["completion_tokens"],
                    mcp_tokens=r["mcp_tokens"],
                    skill_tokens=r["skill_tokens"],
                    system_tokens=r["system_tokens"],
                ),
            )
            for r in rows
        ]

    # ─── Request Logs ────────────────────────────────────────────────

    async def save_request_log(
        self,
        session_id: str,
        request_id: str,
        model: str,
        messages: list[MessageItem],
        token_breakdown: TokenBreakdown,
        tools: list[dict[str, Any]] | None = None,
        system: str | list[dict[str, Any]] | None = None,
        response_content: str | list[dict[str, Any]] | None = None,
    ) -> None:
        await self.db.execute(
            """INSERT INTO request_logs
               (session_id, request_id, timestamp, model, messages, tools, system,
                total_tokens, prompt_tokens, completion_tokens, mcp_tokens, skill_tokens,
                system_tokens, response_content)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                request_id,
                _now_iso(),
                model,
                _json_dumps([m.model_dump() for m in messages]),
                _json_dumps(tools) if tools else None,
                _json_dumps(system) if isinstance(system, list) else system,
                token_breakdown.total_tokens,
                token_breakdown.prompt_tokens,
                token_breakdown.completion_tokens,
                token_breakdown.mcp_tokens,
                token_breakdown.skill_tokens,
                token_breakdown.system_tokens,
                _json_dumps(response_content) if response_content is not None else None,
            ),
        )
        await self.db.commit()

    async def get_request_logs(
        self, session_id: str, limit: int = 50, offset: int = 0
    ) -> list[RequestLog]:
        rows = await self.db.execute(
            """SELECT * FROM request_logs WHERE session_id = ?
               ORDER BY id DESC LIMIT ? OFFSET ?""",
            (session_id, limit, offset),
        )
        rows = await rows.fetchall()
        return [
            RequestLog(
                id=r["id"],
                session_id=r["session_id"],
                request_id=r["request_id"],
                timestamp=r["timestamp"],
                model=r["model"],
                messages=[MessageItem(**m) for m in _json_loads(r["messages"])],
                tools=_json_loads(r["tools"]),
                system=_json_loads(r["system"]),
                token_breakdown=TokenBreakdown(
                    total_tokens=r["total_tokens"],
                    prompt_tokens=r["prompt_tokens"],
                    completion_tokens=r["completion_tokens"],
                    mcp_tokens=r["mcp_tokens"],
                    skill_tokens=r["skill_tokens"],
                    system_tokens=r["system_tokens"],
                ),
                response_content=_json_loads(r["response_content"]),
            )
            for r in rows
        ]

    # ─── Fork Graph ──────────────────────────────────────────────────

    async def get_fork_graph(self, session_id: str) -> ForkGraph:
        """Build fork graph by walking parent/child links from a given session."""
        lineage_ids: set[str] = set()
        queue = [session_id]
        visited: set[str] = set()

        while queue:
            sid = queue.pop(0)
            if sid in visited:
                continue
            visited.add(sid)
            lineage_ids.add(sid)

            # Get children
            child_rows = await self.db.execute(
                "SELECT session_id FROM sessions WHERE parent_session_id = ?", (sid,)
            )
            children = await child_rows.fetchall()
            for c in children:
                if c["session_id"] not in visited:
                    queue.append(c["session_id"])

            # Get parent
            parent_row = await self.db.execute(
                "SELECT parent_session_id FROM sessions WHERE session_id = ?", (sid,)
            )
            parent = await parent_row.fetchone()
            if parent and parent["parent_session_id"] and parent["parent_session_id"] not in visited:
                queue.append(parent["parent_session_id"])

        # Build nodes
        nodes: list[ForkNode] = []
        edges: list[tuple[str, str]] = []
        for sid in lineage_ids:
            row = await self.db.execute("SELECT * FROM sessions WHERE session_id = ?", (sid,))
            r = await row.fetchone()
            if r is None:
                continue
            token_row = await self.db.execute(
                "SELECT COALESCE(SUM(total_tokens), 0) as total FROM token_records WHERE session_id = ?",
                (sid,),
            )
            token_data = await token_row.fetchone()
            nodes.append(
                ForkNode(
                    session_id=sid,
                    name=r["name"],
                    parent_session_id=r["parent_session_id"],
                    fork_point_token=token_data["total"] if token_data else 0,
                    fork_point_time=r["created_at"],
                    children=[],
                )
            )
            if r["parent_session_id"]:
                edges.append((r["parent_session_id"], sid))

        # Populate children lists
        node_map = {n.session_id: n for n in nodes}
        for parent_id, child_id in edges:
            if parent_id in node_map:
                node_map[parent_id].children.append(child_id)

        return ForkGraph(nodes=nodes, edges=edges)
