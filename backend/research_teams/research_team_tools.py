from __future__ import annotations
from typing import List
import httpx
from langchain_core.tools import tool


@tool
def search_web(query: str) -> str:
	"""Lightweight web search placeholder. Returns a helpful message.
	This environment has no external search provider configured.
	Summarize what you would search and what information you need.
	"""
	return (
		"Search is not enabled in this environment. Please provide specific URLs to scrape, "
		"or describe what information you want me to extract."
	)


@tool
def scrape_webpages(urls: List[str]) -> str:
	"""Fetch the provided web pages using httpx and return their raw text content concatenated."""
	texts: List[str] = []
	for url in urls:
		try:
			resp = httpx.get(url, timeout=15)
			resp.raise_for_status()
			texts.append(f"<Document url=\"{url}\">\n{resp.text[:10000]}\n</Document>")
		except Exception as e:
			texts.append(f"<Document url=\"{url}\">\nERROR: {e}\n</Document>")
	return "\n\n".join(texts)


# Convenient export for team wiring
RESEARCH_TEAM_TOOLS = [search_web, scrape_webpages]
__all__ = ["search_web", "scrape_webpages", "RESEARCH_TEAM_TOOLS"]
