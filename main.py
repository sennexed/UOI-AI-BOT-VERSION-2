"""Main entrypoint for UOI Discord AI Bot."""

from __future__ import annotations

import asyncio
import os
from typing import List

import discord
from groq import APIError, Groq, RateLimitError

from characteristics import get_system_prompt
from fandom import search_fandom
from memory_manager import MemoryManager
from quicklink import build_quicklink
from repository_manager import RepositoryManager
from setup_manager import SetupManager
from token_manager import TokenManager
from usage_counter import update_and_format_usage
from website import StatusWebsite


BOT_PREFIX = "UOI "
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)
memory_manager = MemoryManager()
repository_manager = RepositoryManager("repository.json")
token_manager = TokenManager("token_stats.json")
setup_manager = SetupManager("setup_config.json")

website_port = int(os.getenv("PORT", "8080"))
status_website = StatusWebsite(token_manager.get_stats, port=website_port)
status_website.start()


def _build_messages(user_id: int, user_prompt: str) -> List[dict]:
    repo_entries = repository_manager.get_latest_entries(limit=3)
    memory_messages = memory_manager.get_session_messages(user_id)

    repository_context = "\n".join(
        f"- [{entry.get('timestamp', '')}] {entry.get('content', '')}"
        for entry in repo_entries
    ) or "- No repository memory yet."

    messages: List[dict] = [
        {"role": "system", "content": get_system_prompt()},
        {
            "role": "system",
            "content": f"Latest repository memory (most recent first):\n{repository_context}",
        },
    ]

    messages.extend(memory_messages)
    messages.append({"role": "user", "content": user_prompt})
    return messages


async def _call_groq(messages: List[dict]):
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")

    groq_client = Groq(api_key=GROQ_API_KEY)

    def _request():
        return groq_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.7,
        )

    return await asyncio.to_thread(_request)


@client.event
async def on_ready() -> None:
    print(f"Logged in as {client.user} (id={client.user.id if client.user else 'unknown'})")


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    content = (message.content or "").strip()
    if not content.startswith(BOT_PREFIX):
        return

    if message.guild:
        allowed_channel = setup_manager.get_channel(message.guild.id)
        if allowed_channel and message.channel.id != allowed_channel:
            return

    command_body = content[len(BOT_PREFIX):].strip()
    if not command_body:
        return

    lower = command_body.lower()

    if lower == "setup":
        if message.guild is None:
            await message.channel.send("`UOI setup` can only be used inside a server.")
            return
        setup_manager.set_channel(message.guild.id, message.channel.id)
        await message.channel.send(
            f"Setup complete. I will now reply only in {message.channel.mention}."
        )
        return

    if lower == "unset":
        if message.guild is None:
            await message.channel.send("`UOI unset` can only be used inside a server.")
            return
        setup_manager.unset_channel(message.guild.id)
        await message.channel.send("Channel restriction removed for this server.")
        return

    if lower.startswith("link"):
        question = command_body[4:].strip()
        await message.channel.send(build_quicklink(message, question))
        return

    if lower.startswith("fandom"):
        rest = command_body[6:].strip()
        if not rest:
            await message.channel.send("Usage: `UOI fandom <wiki> <topic>`")
            return
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            await message.channel.send("Usage: `UOI fandom <wiki> <topic>`")
            return
        wiki, topic = parts
        await message.channel.send(search_fandom(wiki, topic))
        return

    user_prompt = command_body
    user_id = message.author.id

    try:
        messages = _build_messages(user_id, user_prompt)
        completion = await _call_groq(messages)
    except RuntimeError as exc:
        await message.channel.send(str(exc))
        return
    except RateLimitError:
        await message.channel.send("Groq rate limit reached. Please try again shortly.")
        return
    except APIError:
        await message.channel.send("Groq API error encountered. Please try again in a moment.")
        return
    except Exception:
        await message.channel.send("Unexpected error while generating a response.")
        return

    choices = getattr(completion, "choices", [])
    reply_text = ""
    if choices:
        first_choice = choices[0]
        if getattr(first_choice, "message", None):
            reply_text = getattr(first_choice.message, "content", "") or ""

    if not reply_text.strip():
        await message.channel.send("I received an empty response from the model. Please retry.")
        return

    # Store conversation only in session memory (NOT repository)
    memory_manager.add_message(user_id, "user", user_prompt)
    memory_manager.add_message(user_id, "assistant", reply_text)
    memory_manager.clear_expired_sessions()

    if user_id in ADMIN_IDS:
        reply_text += update_and_format_usage(
            getattr(completion, "usage", None),
            token_manager,
        )

    await message.channel.send(reply_text)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")
    client.run(DISCORD_TOKEN)
