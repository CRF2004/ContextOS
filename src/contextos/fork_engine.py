"""Fork Engine - session fork management."""

from __future__ import annotations

import logging
from typing import Any

from .models import ForkGraph, ForkNode, ForkRequest, SessionCreate, SessionStatus
from .session_store import SessionStore
from .token_profiler import count_message_tokens

logger = logging.getLogger(__name__)

# Auto-fork threshold: 75% of context window
AUTO_FORK_TOKEN_THRESHOLD_RATIO = 0.75


class ForkEngine:
    """Handles manual and automatic session forking."""

    def __init__(self, store: SessionStore, max_prompt_tokens: int = 180000):
        self.store = store
        self.max_prompt_tokens = max_prompt_tokens

    async def fork(
        self,
        req: ForkRequest,
        carry_state: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Fork a session, creating a child session with carried messages.

        Returns:
            Tuple of (parent_session_id, child_session_id)
        """
        # Get parent session
        parent = await self.store.get_session(req.session_id)
        if parent is None:
            raise ValueError(f"Session {req.session_id} not found")

        # Get parent's recent messages
        logs = await self.store.get_request_logs(req.session_id, limit=req.carry_messages)
        carry_messages = [msg for log in reversed(logs) for msg in log.messages]

        # Archive parent
        await self.store.archive_session(req.session_id)

        # Create child session
        fork_name = req.name or f"{parent.name}-fork" if parent.name else f"fork-of-{req.session_id}"
        child = await self.store.create_session(
            SessionCreate(
                parent_session_id=req.session_id,
                name=fork_name,
                metadata={
                    "forked_from": req.session_id,
                    "carry_messages": len(carry_messages),
                    "carried_state": carry_state or {},
                },
            )
        )

        logger.info(
            f"Forked session {req.session_id} -> {child.session_id} "
            f"(carried {len(carry_messages)} messages)"
        )
        return req.session_id, child.session_id

    async def check_auto_fork(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        model: str,
    ) -> bool:
        """Check if auto-fork should be triggered based on token usage."""
        msg_tokens = count_message_tokens(messages, model)
        threshold = self.max_prompt_tokens * AUTO_FORK_TOKEN_THRESHOLD_RATIO

        if msg_tokens > threshold:
            logger.warning(
                f"Auto-fork triggered for session {session_id}: "
                f"{msg_tokens} tokens > {threshold} threshold"
            )
            return True
        return False

    async def get_fork_graph(self, session_id: str) -> ForkGraph:
        """Get the fork graph for a session lineage."""
        return await self.store.get_fork_graph(session_id)
