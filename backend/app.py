import os
import json
import asyncio
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from backend.utils.callbacks import AsyncQueueCallbackHandler
from graph import super_graph
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# Load environment variables from .env if present
load_dotenv()



BAILIAN_API_KEY = os.getenv("BAILIAN_API_KEY")
BAILIAN_BASE_URL = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
BAILIAN_MODEL = os.getenv("BAILIAN_MODEL", "Moonshot-Kimi-K2-Instruct")

app = FastAPI(title="Hierachical Agent Teams")

llm = ChatOpenAI(
        api_key=BAILIAN_API_KEY,
        base_url=BAILIAN_BASE_URL,
        model=BAILIAN_MODEL,
        temperature=0.3,
        streaming=False,
        callbacks=None,
    )

# Allow local dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/chat/stream")
async def chat_stream(
    message: str = Query(..., min_length=1),
    conversation_id: Optional[str] = Query(None),
) -> StreamingResponse:
    """
    SSE streaming endpoint. Use EventSource on the frontend.
    Query string keeps it simple for SSE (GET-only).
    """
    queue: asyncio.Queue[str] = asyncio.Queue()
    handler = AsyncQueueCallbackHandler(queue)

    # Build a graph bound to this request's callback handler
    app_graph = super_graph(
        api_key=BAILIAN_API_KEY,
        base_url=BAILIAN_BASE_URL,
        model=BAILIAN_MODEL,
        callback_handler=handler,
    )

    async def producer() -> None:
        try:
            await app_graph.ainvoke({
                "messages": [HumanMessage(content=message)],
                "metadata": {"conversation_id": conversation_id},
            })
        except Exception as e:
            await queue.put(json.dumps({"type": "error", "message": str(e)}))
        finally:
            # Signal completion
            await queue.put("[DONE]")

    async def event_publisher() -> AsyncGenerator[bytes, None]:
        # Fire-and-forget the LLM run
        asyncio.create_task(producer())
        while True:
            chunk = await queue.get()
            if chunk == "[DONE]":
                yield b"data: [DONE]\n\n"
                break
            # chunk is already a JSON-encoded string
            yield f"data: {chunk}\n\n".encode("utf-8")

    return StreamingResponse(event_publisher(), media_type="text/event-stream")
