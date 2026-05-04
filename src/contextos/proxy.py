"""Proxy Layer - intercept and forward Claude API requests/responses."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from .context_engine import ContextEngine
from .fork_engine import ForkEngine
from .models import ContextConfig, MessageItem, TokenBreakdown
from .session_store import SessionStore
from .token_profiler import profile_request, profile_response

logger = logging.getLogger(__name__)

# Default Claude API base URL
DEFAULT_CLAUDE_BASE_URL = "https://api.anthropic.com"
CLAUDE_API_VERSION = "2023-06-01"


class ProxyLayer:
    """Proxy that intercepts Claude API requests/responses for token profiling and context control."""

    def __init__(
        self,
        store: SessionStore,
        api_key: str,
        base_url: str = DEFAULT_CLAUDE_BASE_URL,
        context_engine: ContextEngine | None = None,
        fork_engine: ForkEngine | None = None,
    ):
        self.store = store
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.context_engine = context_engine or ContextEngine()
        self.fork_engine = fork_engine
        self._http_client = httpx.AsyncClient(timeout=300.0)

    async def close(self) -> None:
        await self._http_client.aclose()

    async def forward_messages(
        self,
        session_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Forward a /messages request through the proxy.

        Flow:
        1. Extract request data
        2. Profile request tokens
        3. Forward to Claude API
        4. Profile response tokens
        5. Log everything to session store
        """
        # Extract request parts
        model = body.get("model", "claude-3-5-sonnet-20241022")
        messages = body.get("messages", [])
        tools = body.get("tools")
        system = body.get("system")
        stream = body.get("stream", False)

        # Generate request ID
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Profile request
        request_profile = profile_request(messages, model, tools, system)

        # Handle non-streaming
        if not stream:
            response = await self._http_client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": CLAUDE_API_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )

            if response.status_code != 200:
                logger.error(f"Claude API error: {response.status_code} {response.text}")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "body": response.text,
                }

            response_body = response.json()

            # Profile response
            response_profile = profile_response(response_body, model)

            # Merge request + response profiles
            merged = TokenBreakdown(
                total_tokens=response_profile.total_tokens,
                prompt_tokens=response_profile.prompt_tokens,
                completion_tokens=response_profile.completion_tokens,
                mcp_tokens=response_profile.mcp_tokens,
                skill_tokens=request_profile.skill_tokens,
                system_tokens=request_profile.system_tokens,
            )

            # Save to store
            await self.store.save_token_record(session_id, request_id, model, merged)
            await self.store.save_request_log(
                session_id,
                request_id,
                model,
                [MessageItem(role=m.get("role", ""), content=m.get("content", "")) for m in messages],
                merged,
                tools=tools,
                system=system,
                response_content=response_body.get("content"),
            )

            # Check auto-fork
            if self.fork_engine:
                await self.fork_engine.check_auto_fork(session_id, messages, model)

            logger.info(f"[{request_id}] Session {session_id}: {merged.total_tokens} tokens")
            return response_body

        else:
            # Streaming mode: proxy SSE stream
            return await self._forward_stream(session_id, request_id, body, messages, tools, system, model)

    async def _forward_stream(
        self,
        session_id: str,
        request_id: str,
        body: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        system: str | list[dict[str, Any]] | None,
        model: str,
    ) -> dict[str, Any]:
        """Forward a streaming request, collecting the full response for logging."""
        request_profile = profile_request(messages, model, tools, system)

        async with self._http_client.stream(
            "POST",
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": CLAUDE_API_VERSION,
                "content-type": "application/json",
            },
            json=body,
        ) as response:
            # Collect full response from SSE events
            full_content: list[dict[str, Any]] = []
            final_usage = {"input_tokens": 0, "output_tokens": 0}

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json

                    try:
                        event = json.loads(line[6:])
                        if event.get("type") == "content_block_start":
                            block = event.get("content_block", {})
                            full_content.append(block)
                        elif event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                if full_content and full_content[-1].get("type") == "text":
                                    full_content[-1]["text"] += delta.get("text", "")
                        elif event.get("type") == "message_stop":
                            pass
                        elif event.get("type") == "ping":
                            pass
                    except json.JSONDecodeError:
                        pass

            # Build synthetic response for logging
            synthetic_response = {
                "id": request_id,
                "type": "message",
                "role": "assistant",
                "content": full_content,
                "model": model,
                "stop_reason": "end_turn",
                "usage": final_usage,
            }

            response_profile = profile_response(synthetic_response, model)
            merged = TokenBreakdown(
                total_tokens=response_profile.total_tokens if response_profile.total_tokens > 0 else request_profile.prompt_tokens,
                prompt_tokens=response_profile.prompt_tokens or request_profile.prompt_tokens,
                completion_tokens=response_profile.completion_tokens,
                mcp_tokens=response_profile.mcp_tokens,
                skill_tokens=request_profile.skill_tokens,
                system_tokens=request_profile.system_tokens,
            )

            await self.store.save_token_record(session_id, request_id, model, merged)

            return {
                "stream": True,
                "request_id": request_id,
                "content": full_content,
            }
