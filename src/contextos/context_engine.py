"""Context Engine - trimming, pruning, skill injection."""

from __future__ import annotations

import logging
from typing import Any

from .models import ContextConfig, ContextStats, MessageItem
from .token_profiler import count_message_tokens, count_system_tokens, count_tool_tokens

logger = logging.getLogger(__name__)


class ContextEngine:
    """Handles context trimming, tool pruning, and skill injection."""

    def __init__(self, config: ContextConfig | None = None):
        self.config = config or ContextConfig()

    def get_stats(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        system: str | list[dict[str, Any]] | None = None,
    ) -> ContextStats:
        """Calculate current context token usage."""
        message_tokens = count_message_tokens(messages, model)
        tool_tokens = count_tool_tokens(tools or [], model) if tools else 0
        system_tokens = count_system_tokens(system, model) if system else 0

        total = message_tokens + tool_tokens + system_tokens
        return ContextStats(
            total_tokens=total,
            message_tokens=message_tokens,
            tool_tokens=tool_tokens,
            skill_tokens=0,
            system_tokens=system_tokens,
            message_count=len(messages),
            tool_count=len(tools) if tools else 0,
        )

    def needs_trimming(self, messages: list[dict[str, Any]], model: str) -> bool:
        """Check if context needs trimming based on token budget."""
        msg_tokens = count_message_tokens(messages, model)
        return msg_tokens > self.config.max_prompt_tokens * 0.8  # 80% threshold

    def trim_messages(
        self,
        messages: list[dict[str, Any]],
        model: str,
        summary: str | None = None,
    ) -> list[dict[str, Any]]:
        """Trim message history to fit within token budget.

        Strategy:
        1. Keep the last `keep_recent_messages` messages unchanged.
        2. If still over budget, progressively drop oldest messages.
        3. Optionally insert a summary at the top.
        """
        if len(messages) <= self.config.keep_recent_messages:
            return messages

        recent = messages[-self.config.keep_recent_messages :]
        old = messages[: -self.config.keep_recent_messages]

        # Check if trimming is needed
        current_tokens = count_message_tokens(old + recent, model)
        if current_tokens <= self.config.max_prompt_tokens * 0.5:
            return messages

        if summary:
            # Prepend summary as a user message
            summary_msg = {"role": "user", "content": f"[Conversation Summary]\n{summary}"}
            result = [summary_msg] + recent
        else:
            # Just keep recent messages
            result = recent

        logger.info(f"Trimmed {len(messages)} messages to {len(result)}")
        return result

    def prune_tools(
        self,
        tools: list[dict[str, Any]],
        model: str,
    ) -> list[dict[str, Any]]:
        """Prune tool definitions to fit within budget."""
        if len(tools) <= self.config.max_tools:
            return tools

        # For now, keep the first N tools (priority ordering by registration)
        # Future: could use relevance scoring based on message content
        pruned = tools[: self.config.max_tools]
        logger.info(f"Pruned {len(tools)} tools to {len(pruned)}")
        return pruned

    def inject_skill(
        self,
        system_prompt: str | list[dict[str, Any]] | None,
        skill_prompt: str,
    ) -> str | list[dict[str, Any]]:
        """Inject a skill prompt into the system message."""
        skill_block = {"type": "text", "text": skill_prompt}

        if system_prompt is None:
            return skill_block
        elif isinstance(system_prompt, str):
            # Merge with existing system prompt
            combined = f"{system_prompt}\n\n<skill>\n{skill_prompt}\n</skill>"
            return combined
        elif isinstance(system_prompt, list):
            return system_prompt + [skill_block]

        return system_prompt

    def apply_context_config(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        system: str | list[dict[str, Any]] | None,
        model: str,
        summary: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None, str | list[dict[str, Any]] | None]:
        """Apply full context configuration: trim + prune."""
        # Trim messages
        messages = self.trim_messages(messages, model, summary)

        # Prune tools
        if tools:
            tools = self.prune_tools(tools, model)

        return messages, tools, system
