"""
Sorachio-STS Web Search Engine.
Lightweight instant web search using DuckDuckGo (no API keys required).
Fully fault-tolerant with offline fallback.
"""

from __future__ import annotations

import asyncio
from typing import Any

from utils.logging_setup import get_logger

log = get_logger("utils.web_search")

try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False
    DDGS = None


class WebSearchEngine:
    """Instant web search utility for Sorachio agentic search actions."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    async def search(self, query: str, max_results: int = 3) -> str:
        """
        Execute web search for query and return text summary.

        Args:
            query: Search query string.
            max_results: Max search snippets to include.

        Returns:
            Concatenated summary string suitable for LLM context injection.
        """
        if not self.enabled:
            return "Web search is disabled in settings."

        if not DUCKDUCKGO_AVAILABLE:
            return "duckduckgo-search package is not installed."

        log.info(f"[WebSearch] Searching for: '{query}'")

        try:
            # Run DuckDuckGo search in thread to avoid blocking asyncio event loop
            def _sync_search() -> list[dict[str, Any]]:
                if DDGS is None:
                    return []
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))

            results = await asyncio.to_thread(_sync_search)

            if not results:
                return f"No web search results found for '{query}'."

            snippets: list[str] = []
            for item in results:
                title = item.get("title", "")
                body = item.get("body", "")
                if title or body:
                    snippets.append(f"- {title}: {body}")

            summary = "\n".join(snippets)
            log.info(f"[WebSearch] Retrieved {len(snippets)} snippets for '{query}'")
            return summary

        except Exception as e:
            log.warning(f"[WebSearch] Search failed (network offline or rate limited): {e}")
            return f"Web search failed due to network connection issues ({e})."
