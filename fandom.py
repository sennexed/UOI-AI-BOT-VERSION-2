"""Fandom API search helper."""

from __future__ import annotations

import requests


REQUEST_TIMEOUT = 10


def search_fandom(wiki: str, topic: str) -> str:
    """Search a Fandom wiki and return a concise summary."""
    wiki = wiki.strip().lower()
    topic = topic.strip()
    if not wiki or not topic:
        return "Usage: `UOI fandom <wiki> <topic>`"

    url = f"https://{wiki}.fandom.com/api/v1/Search/List"
    params = {"query": topic, "limit": 1}

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            return "That wiki was not found."
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return "Fandom search is temporarily unavailable."

    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not items:
        return f"No Fandom results found for `{topic}` on `{wiki}`."

    first = items[0]
    title = first.get("title", topic)
    excerpt = first.get("abstract", "No summary available.")
    page_url = first.get("url", f"https://{wiki}.fandom.com")

    clean_excerpt = " ".join(excerpt.split())
    return f"**{title}**\n{clean_excerpt}\n<{page_url}>"
