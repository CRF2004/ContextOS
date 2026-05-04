"""CLI entry point for ContextOS."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import uvicorn

from .session_store import SessionStore


def cmd_run(args: argparse.Namespace) -> None:
    """Start the ContextOS proxy server."""
    import os

    os.environ.setdefault("PROXY_HOST", args.host)
    os.environ.setdefault("PROXY_PORT", str(args.port))
    os.environ.setdefault("DATABASE_PATH", args.db)

    if args.api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.api_key
    if args.base_url:
        os.environ["ANTHROPIC_BASE_URL"] = args.base_url

    print(f"Starting ContextOS on {args.host}:{args.port}")
    print(f"Database: {args.db}")
    print(f"Dashboard: http://{args.host}:{args.port}")
    print()

    uvicorn.run(
        "contextos.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


async def _cmd_sessions(args: argparse.Namespace) -> None:
    """List sessions."""
    store = SessionStore(args.db)
    await store.connect()
    try:
        sessions = await store.list_sessions(limit=args.limit)
        print(f"{'Session ID':<30} {'Name':<20} {'Status':<10} {'Tokens':<12} {'Created'}")
        print("-" * 100)
        for s in sessions:
            print(f"{s.session_id:<30} {s.name or '-':<20} {s.status.value:<10} {s.total_tokens:<12} {s.created_at[:19]}")
    finally:
        await store.close()


async def _cmd_tokens(args: argparse.Namespace) -> None:
    """Show token usage for a session."""
    store = SessionStore(args.db)
    await store.connect()
    try:
        summary = await store.get_token_summary(args.session_id)
        print(f"Session: {summary.session_id}")
        print(f"Total requests: {summary.total_requests}")
        print(f"Total tokens:   {summary.total_tokens:,}")
        print(f"  Prompt:       {summary.total_prompt_tokens:,}")
        print(f"  Completion:   {summary.total_completion_tokens:,}")
        print(f"  MCP tools:    {summary.total_mcp_tokens:,}")
        print(f"  Skills:       {summary.total_skill_tokens:,}")
        print(f"  System:       {summary.total_system_tokens:,}")
    finally:
        await store.close()


async def _cmd_logs(args: argparse.Namespace) -> None:
    """Show request logs for a session."""
    store = SessionStore(args.db)
    await store.connect()
    try:
        logs = await store.get_request_logs(args.session_id, limit=args.limit)
        for log in logs:
            print(f"\n[{log.timestamp[:19]}] Request {log.request_id}")
            print(f"  Model: {log.model}")
            print(f"  Tokens: {log.token_breakdown.total_tokens:,}")
            print(f"  Messages: {len(log.messages)}")
            if log.response_content:
                content = log.response_content
                if isinstance(content, list):
                    text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                    preview = " ".join(text_parts)[:200]
                else:
                    preview = str(content)[:200]
                print(f"  Response: {preview}...")
    finally:
        await store.close()


def cmd_sessions(args: argparse.Namespace) -> None:
    asyncio.run(_cmd_sessions(args))


def cmd_tokens(args: argparse.Namespace) -> None:
    asyncio.run(_cmd_tokens(args))


def cmd_logs(args: argparse.Namespace) -> None:
    asyncio.run(_cmd_logs(args))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="contextos",
        description="ContextOS - Claude Context Operating System",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_parser = subparsers.add_parser("run", help="Start the proxy server")
    run_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    run_parser.add_argument("--port", type=int, default=8199, help="Bind port")
    run_parser.add_argument("--db", default="./contextos.db", help="Database path")
    run_parser.add_argument("--api-key", default=None, help="Anthropic API key")
    run_parser.add_argument("--base-url", default=None, help="Claude API base URL")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    run_parser.set_defaults(func=cmd_run)

    # sessions
    sess_parser = subparsers.add_parser("sessions", help="List sessions")
    sess_parser.add_argument("--db", default="./contextos.db", help="Database path")
    sess_parser.add_argument("--limit", type=int, default=20)
    sess_parser.set_defaults(func=cmd_sessions)

    # tokens
    tok_parser = subparsers.add_parser("tokens", help="Show token usage")
    tok_parser.add_argument("session_id", help="Session ID")
    tok_parser.add_argument("--db", default="./contextos.db", help="Database path")
    tok_parser.set_defaults(func=cmd_tokens)

    # logs
    log_parser = subparsers.add_parser("logs", help="Show request logs")
    log_parser.add_argument("session_id", help="Session ID")
    log_parser.add_argument("--db", default="./contextos.db", help="Database path")
    log_parser.add_argument("--limit", type=int, default=10)
    log_parser.set_defaults(func=cmd_logs)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
