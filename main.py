"""Main entrypoint for UOI Discord AI Bot."""

from __future__ import annotations

import asyncio
import os
from typing import List, Tuple

import discord
from discord import app_commands
from groq import APIError, Groq, RateLimitError

from characteristics import get_system_prompt
from fandom import search_fandom
from logger import BotLogger
from memory_manager import MemoryManager
from repository_manager import RepositoryManager
from setup_manager import SetupManager
from token_manager import TokenManager
from usage_counter import update_and_format_usage
from website import StatusWebsite


BOT_PREFIX = "UOI "
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
DAILY_TOKEN_LIMIT = int(os.getenv("DAILY_TOKEN_LIMIT", "200000"))
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
tree = app_commands.CommandTree(client)
memory_manager = MemoryManager()
repository_manager = RepositoryManager("repository.json")
token_manager = TokenManager("token_stats.json")
setup_manager = SetupManager("setup_config.json")
bot_logger = BotLogger("logs.txt")

website_port = int(os.getenv("PORT", "8080"))
status_website = StatusWebsite(token_manager.get_stats, port=website_port)
status_website.start()

SYNCED = False


def _build_messages(user_id: int, user_prompt: str) -> List[dict]:
    repo_entries = repository_manager.get_latest_entries(limit=3)
    memory_messages = memory_manager.get_session_messages(user_id)

    messages: List[dict] = [{"role": "system", "content": get_system_prompt()}]

    if repo_entries:
        repository_context = "\n".join(
            f"- [{entry.get('timestamp', '')}] {entry.get('content', '')}" for entry in repo_entries
        )
        messages.append(
            {
                "role": "system",
                "content": f"Latest repository memory (most recent first):\n{repository_context}",
            }
        )

    messages.extend(memory_messages)
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _usage_state() -> Tuple[float, int]:
    stats = token_manager.get_stats()
    daily_tokens = int(stats.get("daily_tokens", 0))
    ratio = (daily_tokens / DAILY_TOKEN_LIMIT) if DAILY_TOKEN_LIMIT > 0 else 0.0
    return ratio, daily_tokens


def _select_model() -> str:
    ratio, _ = _usage_state()
    if ratio > 0.80:
        return FALLBACK_MODEL
    return DEFAULT_MODEL


async def _call_groq(messages: List[dict], model_name: str):
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")

    groq_client = Groq(api_key=GROQ_API_KEY)

    def _request():
        return groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
        )

    return await asyncio.to_thread(_request)


def _extract_usage(completion) -> tuple[int, int, int]:
    usage = getattr(completion, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
    return prompt_tokens, completion_tokens, total_tokens


def _build_embed(reply_text: str, is_admin: bool, usage_text: str = "", warning: str = "") -> discord.Embed:
    embed = discord.Embed(
        title="UOI AI",
        description=reply_text,
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )

    if warning:
        embed.add_field(name="Usage Notice", value=warning, inline=False)

    footer_text = "Union of Indians | Powered by Groq"
    if is_admin and usage_text:
        footer_text += f" | {usage_text}"
    embed.set_footer(text=footer_text)
    return embed


@client.event
async def on_ready() -> None:
    global SYNCED
    if not SYNCED:
        await tree.sync()
        SYNCED = True
    print(f"Logged in as {client.user} (id={client.user.id if client.user else 'unknown'})")


@tree.command(name="setup", description="Restrict UOI AI prefix replies to this channel for this server.")
async def setup_channel(interaction: discord.Interaction) -> None:
    if interaction.guild is None or interaction.channel is None:
        await interaction.response.send_message("This command can only be used in a server channel.", ephemeral=True)
        return
    setup_manager.set_channel(interaction.guild.id, interaction.channel.id)
    await interaction.response.send_message(f"Setup complete. Prefix AI replies restricted to {interaction.channel.mention}.")


@tree.command(name="unset", description="Remove server channel restriction for UOI AI prefix replies.")
async def unset_channel(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    setup_manager.unset_channel(interaction.guild.id)
    await interaction.response.send_message("Channel restriction removed for this server.")


@tree.command(name="link", description="Generate a quick Discord link for a channel.")
@app_commands.describe(channel="Channel to generate a direct quicklink for")
async def link_channel(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    url = f"https://discord.com/channels/{interaction.guild.id}/{channel.id}"
    await interaction.response.send_message(f"[{channel.mention}]({url})")


@tree.command(name="fandom", description="Search a Fandom wiki for a topic summary.")
@app_commands.describe(wiki="Fandom wiki subdomain", topic="Search topic")
async def fandom_lookup(interaction: discord.Interaction, wiki: str, topic: str) -> None:
    await interaction.response.defer(thinking=True)
    result = search_fandom(wiki, topic)
    await interaction.followup.send(result)


@tree.command(name="remember", description="Store a curated global repository memory entry.")
@app_commands.describe(note="Memory entry to store")
async def remember_entry(interaction: discord.Interaction, note: str) -> None:
    repository_manager.add_entry(note.strip())
    await interaction.response.send_message("Repository memory entry stored.")


@tree.command(name="repository", description="Show latest repository memory entries.")
async def show_repository(interaction: discord.Interaction) -> None:
    entries = repository_manager.get_latest_entries(limit=3)
    if not entries:
        await interaction.response.send_message("Repository memory is currently empty.", ephemeral=True)
        return
    formatted = "\n\n".join(
        f"`{idx + 1}.` [{entry.get('timestamp', 'unknown')}] {entry.get('content', '')}"
        for idx, entry in enumerate(entries)
    )
    await interaction.response.send_message(f"**Latest Repository Entries**\n{formatted}")


@tree.command(name="forget", description="Remove the newest repository memory entry.")
async def forget_entry(interaction: discord.Interaction) -> None:
    removed = repository_manager.remove_latest_entry()
    if not removed:
        await interaction.response.send_message("Repository memory is already empty.", ephemeral=True)
        return
    await interaction.response.send_message("Removed the latest repository memory entry.")


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

    user_prompt = content[len(BOT_PREFIX) :].strip()
    if not user_prompt:
        return

    usage_ratio, daily_tokens = _usage_state()
    if usage_ratio > 0.95:
        await message.channel.send("Daily token quota exceeded. Please try again after 00:00 UTC reset.")
        return

    model_name = _select_model()
    warning_text = ""
    if usage_ratio > 0.80:
        warning_text = (
            f"Usage is above 80% ({daily_tokens}/{DAILY_TOKEN_LIMIT}). "
            "Fallback model is active to conserve quota."
        )

    try:
        messages = _build_messages(message.author.id, user_prompt)
        completion = await _call_groq(messages, model_name)
    except RuntimeError as exc:
        await message.channel.send(str(exc))
        bot_logger.log_error("groq_runtime", exc)
        return
    except RateLimitError as exc:
        await message.channel.send("Groq rate limit reached. Please try again shortly.")
        bot_logger.log_error("groq_rate_limit", exc)
        return
    except APIError as exc:
        await message.channel.send("Groq API error encountered. Please try again in a moment.")
        bot_logger.log_error("groq_api", exc)
        return
    except Exception as exc:
        await message.channel.send("Unexpected error while generating a response.")
        bot_logger.log_error("on_message_generation", exc)
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

    memory_manager.add_message(message.author.id, "user", user_prompt)
    memory_manager.add_message(message.author.id, "assistant", reply_text)
    memory_manager.clear_expired_sessions()

    usage_text = update_and_format_usage(getattr(completion, "usage", None), token_manager)
    prompt_tokens, completion_tokens, total_tokens = _extract_usage(completion)
    bot_logger.log_prompt(
        user_id=message.author.id,
        username=message.author.name,
        prompt=user_prompt,
        model_used=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    is_admin = message.author.id in ADMIN_IDS
    compact_usage = (
        usage_text.replace("**Token Usage**", "").replace("\n", " ").replace("-", "|").strip()
        if is_admin
        else ""
    )
    embed = _build_embed(reply_text=reply_text, is_admin=is_admin, usage_text=compact_usage, warning=warning_text)
    await message.channel.send(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")
    client.run(DISCORD_TOKEN)
