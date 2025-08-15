from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.outputs import LLMResult


class AsyncQueueCallbackHandler(AsyncCallbackHandler):
    """A LangChain async callback handler that pushes tokens to an asyncio.Queue.

    The FastAPI SSE endpoint consumes messages from the queue and forwards them to the client.
    """

    def __init__(self, queue: asyncio.Queue[str]):
        self.queue = queue

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:  # type: ignore[override]
        payload: Dict[str, Any] = {"type": "token", "content": token}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:  # type: ignore[override]
        payload: Dict[str, Any] = {"type": "end"}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:  # type: ignore[override]
        payload: Dict[str, Any] = {"type": "error", "message": str(error)}
        await self.queue.put(json.dumps(payload, ensure_ascii=False))
