"""Helpers for applying and formatting token usage details."""

from __future__ import annotations

from typing import Any

from token_manager import TokenManager


def update_and_format_usage(usage: Any, token_manager: TokenManager) -> str:
    """Update token counters from a Groq usage object and return a summary text."""
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)

    stats = token_manager.update_usage(prompt_tokens, completion_tokens, total_tokens)

    return (
        "\n\n**Token Usage**\n"
        f"- This Message tokens: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}\n"
        f"- Daily total: {stats['daily_tokens']}\n"
        f"- Lifetime total: {stats['total_tokens']}"
    )
