"""Discord quicklink utility."""

from __future__ import annotations

import re

import discord


CHANNEL_MENTION_PATTERN = re.compile(r"<#(\d+)>")


def build_quicklink(message: discord.Message, question: str) -> str:
    """Return a quicklink markdown URL for a mentioned channel."""
    match = CHANNEL_MENTION_PATTERN.search(question)
    if not match:
        return "Please mention a channel, e.g. `UOI link #general`."

    channel_id = int(match.group(1))
    guild = message.guild
    if guild is None:
        return "This command can only be used in a server channel."

    channel = guild.get_channel(channel_id)
    if channel is None:
        return "I could not find that channel in this server."

    url = f"https://discord.com/channels/{guild.id}/{channel.id}"
    return f"[{channel.mention}]({url})"
