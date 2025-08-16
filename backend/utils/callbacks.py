from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Set

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from .context import current_team, current_node


class AsyncQueueCallbackHandler(AsyncCallbackHandler):

    def __init__(self, queue: asyncio.Queue[str]):
        self.queue = queue
        self._suppress_runs: Set[str] = set()
        self._buffers: Dict[str, str] = {}

    def _is_supervisor_prompt(self, messages: Any) -> bool:
        try:
            for m in messages or []:
                content = getattr(m, "content", None)
                if not content and isinstance(m, dict):
                    content = m.get("content")
                if not content:
                    continue
                text = str(content).lower()
                # Suppress routing decisions and JSON responses
                if (("you are a supervisor" in text and "finish" in text and 
                    "json format" in text) or
                    ("next worker" in text) or
                    ("respond with json" in text) or
                    ("respond in json format" in text)):
                    return True
        except Exception:
            pass
        return False

    def _contains_routing_json(self, content: str) -> bool:
        """Check if content contains JSON routing decisions like {"next": "agent_name"}"""
        try:
            content_lower = content.lower().strip()
            # Check for JSON routing patterns
            if (content_lower.startswith('{') and content_lower.endswith('}') and
                ('"next"' in content_lower or "'next'" in content_lower)):
                return True
            # Check for other routing indicators
            routing_patterns = [
                '{"next":',
                "{'next':",
                '"decision":',
                '"route":',
                '"goto":'
            ]
            return any(pattern in content_lower for pattern in routing_patterns)
        except Exception:
            pass
        return False

    def _contains_supervisor_keywords(self, content: str) -> bool:
        """Check if content contains supervisor routing keywords that should be suppressed"""
        try:
            content_lower = content.lower().strip()
            # Common supervisor routing keywords
            supervisor_keywords = [
                'search', 'web_scraper', 'doc_writer', 'note_taker', 'chart_generator',
                'finish', 'complete', 'research_team', 'writing_team', 'document_team'
            ]
            # Check if content is just a single keyword (likely a routing decision)
            if content_lower in supervisor_keywords:
                return True
            # Check if content starts with these keywords followed by common patterns
            for keyword in supervisor_keywords:
                if (content_lower.startswith(keyword) and
                    len(content_lower.split()) <= 2):  # Short phrases likely routing
                    return True
        except Exception:
            pass
        return False


    # --- ChatModel streaming (preferred in langchain>=0.2) ---
    async def on_chat_model_start(self, serialized: Dict[str, Any], messages: Any, **kwargs: Any) -> None:  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        team = current_team.get("")

        # STRICT FILTERING: Only allow output from final team
        # Suppress everything that's not explicitly from the final team
        should_suppress = team != "final"

        # Always suppress supervisor/routing messages regardless of team
        if self._is_supervisor_prompt(messages):
            should_suppress = True

        if should_suppress and run_id:
            self._suppress_runs.add(run_id)
        elif run_id:
            # initialize buffer for this run
            self._buffers[run_id] = ""
        return None

    async def on_chat_model_stream(self, chunk: Any, **kwargs: Any) -> None:  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        if run_id and run_id in self._suppress_runs:
            return

        # STRICT CHECK: only allow streaming from final team
        team = current_team.get("")
        if team != "final":
            return

        content = getattr(chunk, "content", None)
        if content:
            text = str(content)

            # Check if this chunk contains routing JSON or supervisor keywords
            current_buffer = self._buffers.get(run_id, "") + text
            if (self._contains_routing_json(current_buffer) or
                self._contains_supervisor_keywords(current_buffer)):
                # Mark this run for suppression
                if run_id:
                    self._suppress_runs.add(run_id)
                return

            if run_id:
                self._buffers[run_id] = current_buffer

            payload: Dict[str, Any] = {
                "type": "token",
                "content": text,
            }
            if team:
                payload["team"] = team
            node = current_node.get("")
            if node:
                payload["node"] = node
            await self.queue.put(json.dumps(payload, ensure_ascii=False))

    async def on_chat_model_end(self, response: Any, **kwargs: Any) -> None:  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        if run_id and run_id in self._suppress_runs:
            self._suppress_runs.discard(run_id)
            return  # Don't send end event for suppressed runs
        # Clean up buffer
        text = self._buffers.pop(run_id, "") if run_id else ""

        # Only send end event for final team
        team = current_team.get("")
        if team == "final":
            payload: Dict[str, Any] = {"type": "end"}
            await self.queue.put(json.dumps(payload, ensure_ascii=False))

    async def on_chat_model_error(self, error: Exception, **kwargs: Any) -> None:  # type: ignore[override]
        payload: Dict[str, Any] = {"type": "error", "message": str(error)}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))

    # --- Legacy LLM callbacks (for completeness) ---
    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:  # type: ignore[override]
        # Apply same filtering as chat model
        team = current_team.get("")
        if team != "final":
            return
        payload: Dict[str, Any] = {"type": "token", "content": token}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:  # type: ignore[override]
        # Apply same filtering as chat model
        team = current_team.get("")
        if team != "final":
            return
        payload: Dict[str, Any] = {"type": "end"}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:  # type: ignore[override]
        payload: Dict[str, Any] = {"type": "error", "message": str(error)}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))
