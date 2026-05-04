"""FastAPI server - main application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from .context_engine import ContextEngine
from .fork_engine import ForkEngine, ForkRequest
from .models import (
    ContextConfig,
    ContextStats,
    ForkGraph,
    MessageItem,
    RequestLog,
    SessionCreate,
    SessionResponse,
    TokenRecord,
    TokenSummary,
)
from .proxy import ProxyLayer
from .session_store import SessionStore
from .token_profiler import count_tokens

logger = logging.getLogger("contextos")

# Global state
store: SessionStore | None = None
proxy: ProxyLayer | None = None
context_engine: ContextEngine | None = None
fork_engine: ForkEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, proxy, context_engine, fork_engine

    # Read config from env
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "") or None
    db_path = os.environ.get("DATABASE_PATH", "./contextos.db")

    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — proxy will not forward to Claude API")

    # Initialize store
    store = SessionStore(db_path=db_path)
    await store.connect()
    logger.info(f"SessionStore connected to {db_path}")

    # Initialize engines
    context_engine = ContextEngine()
    fork_engine = ForkEngine(store)

    # Initialize proxy
    proxy = ProxyLayer(
        store=store,
        api_key=api_key,
        base_url=base_url or "https://api.anthropic.com",
        context_engine=context_engine,
        fork_engine=fork_engine,
    )
    logger.info("ProxyLayer initialized")

    yield

    # Cleanup
    if proxy:
        await proxy.close()
    if store:
        await store.close()


# ─── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ContextOS",
    description="Claude Context Operating System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Session APIs ─────────────────────────────────────────────────────────


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(req: SessionCreate):
    """Create a new session."""
    assert store is not None
    return await store.create_session(req)


@app.get("/api/sessions", response_model=list[SessionResponse])
async def list_sessions(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """List sessions."""
    assert store is not None
    return await store.list_sessions(limit=limit, offset=offset)


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details."""
    assert store is not None
    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(404, f"Session {session_id} not found")
    return session


@app.post("/api/sessions/{session_id}/archive")
async def archive_session(session_id: str):
    """Archive a session."""
    assert store is not None
    await store.archive_session(session_id)
    return {"status": "ok", "session_id": session_id}


# ─── Token APIs ───────────────────────────────────────────────────────────


@app.get("/api/sessions/{session_id}/tokens", response_model=TokenSummary)
async def get_token_summary(session_id: str):
    """Get token usage summary for a session."""
    assert store is not None
    return await store.get_token_summary(session_id)


@app.get("/api/sessions/{session_id}/tokens/history", response_model=list[TokenRecord])
async def get_token_history(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get token history for a session."""
    assert store is not None
    return await store.get_token_history(session_id, limit=limit, offset=offset)


# ─── Request Log APIs ─────────────────────────────────────────────────────


@app.get("/api/sessions/{session_id}/requests", response_model=list[RequestLog])
async def get_request_logs(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get request logs for a session."""
    assert store is not None
    return await store.get_request_logs(session_id, limit=limit, offset=offset)


# ─── Context Engine APIs ──────────────────────────────────────────────────


class ContextStatsRequest(BaseModel):
    messages: list[MessageItem]
    model: str = "claude-3-5-sonnet-20241022"
    tools: list[dict[str, Any]] | None = None
    system: str | list[dict[str, Any]] | None = None


@app.post("/api/context/stats", response_model=ContextStats)
async def get_context_stats(req: ContextStatsRequest):
    """Calculate context token stats for given messages."""
    assert context_engine is not None
    messages_dict = [
        {"role": m.role, "content": m.content} for m in req.messages
    ]
    return context_engine.get_stats(messages_dict, req.model, req.tools, req.system)


# ─── Fork APIs ────────────────────────────────────────────────────────────


@app.post("/api/sessions/{session_id}/fork", response_model=SessionResponse)
async def fork_session(session_id: str, req: ForkRequest):
    """Fork a session."""
    assert store is not None
    assert fork_engine is not None

    if req.session_id != session_id:
        raise HTTPException(400, "session_id mismatch")

    parent_id, child_id = await fork_engine.fork(req)
    child = await store.get_session(child_id)
    assert child is not None
    return child


@app.get("/api/sessions/{session_id}/fork-graph", response_model=ForkGraph)
async def get_fork_graph(session_id: str):
    """Get fork graph for a session lineage."""
    assert fork_engine is not None
    return await fork_engine.get_fork_graph(session_id)


# ─── Proxy Endpoint ──────────────────────────────────────────────────────


@app.post("/api/proxy/messages")
async def proxy_messages(
    body: dict[str, Any],
    session_id: str = Query(..., description="Session ID to associate with this request"),
):
    """Proxy endpoint: forward Claude API /messages request."""
    assert proxy is not None
    result = await proxy.forward_messages(session_id, body)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(result.get("status_code", 500), str(result.get("body")))
    return result


# ─── Health ───────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "0.1.0"}


# ─── Token counter utility ───────────────────────────────────────────────


class TokenCountRequest(BaseModel):
    text: str
    model: str = "claude-3-5-sonnet-20241022"


@app.post("/api/tokens/count")
async def count_tokens_endpoint(req: TokenCountRequest):
    """Count tokens in a text string."""
    return {"tokens": count_tokens(req.text, req.model)}


# ─── Static Web UI (SPA) ─────────────────────────────────────────────────


_STATIC_DIR = Path(__file__).parent.parent.parent / "dist" / "web"


@app.get("/assets/{file_path:path}")
async def serve_asset(file_path: str):
    """Serve static asset files."""
    asset_path = _STATIC_DIR / "assets" / file_path
    if asset_path.is_file():
        return FileResponse(asset_path)
    raise HTTPException(404, f"Asset not found: {file_path}")


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(full_path: str):
    """Catch-all: serve the SPA index.html for any non-API route."""
    # Don't handle API routes
    if full_path.startswith("api/"):
        raise HTTPException(404)
    index_path = _STATIC_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return HTMLResponse(
        content="""<!doctype html>
        <html><head><title>ContextOS</title></head>
        <body><h1>ContextOS</h1><p>Build the web UI first: <code>cd web && npm run build</code></p></body></html>""",
    )
