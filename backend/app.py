import os
import json
import asyncio
import logging
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from utils.callbacks import AsyncQueueCallbackHandler
from graph import build_super_graph
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from utils.context import (
    init_request_context, update_request_status
)

# Configure logging for hierarchical agent teams
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env if present
load_dotenv()

BAILIAN_API_KEY = os.getenv("BAILIAN_API_KEY")
BAILIAN_BASE_URL = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
BAILIAN_MODEL = os.getenv("BAILIAN_MODEL", "Moonshot-Kimi-K2-Instruct")

app = FastAPI(
    title="Hierarchical Agent Teams",
    description="AI-powered hierarchical agent coordination system",
    version="1.0.0"
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
    """Health check endpoint for hierarchical agent teams."""
    try:
        # Basic health check - could be extended with dependency checks
        return {
            "status": "healthy",
            "service": "hierarchical-agent-teams",
            "version": "1.0.0",
            "components": {
                "super_graph": "operational",
                "context_management": "operational",
                "streaming": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/api/chat/stream")
async def chat_stream(
    message: str = Query(..., min_length=1, description="User message for hierarchical agent processing"),
    conversation_id: Optional[str] = Query(None, description="Optional conversation identifier"),
) -> StreamingResponse:
    request_id = None
    
    try:
        request_id = init_request_context(conversation_id, message)
        logger.info(f"Processing hierarchical agent request: {request_id}")
        
        queue: asyncio.Queue[str] = asyncio.Queue()
        handler = AsyncQueueCallbackHandler(queue)

        llm_stream = ChatOpenAI(
            api_key=BAILIAN_API_KEY,
            base_url=BAILIAN_BASE_URL,
            model=BAILIAN_MODEL,
            temperature=0.3,
            streaming=True,
            callbacks=[handler],
        )
        streaming_graph = build_super_graph(llm_stream)

        async def producer() -> None:
            """Execute hierarchical agent workflow with comprehensive error handling."""
            try:
                update_request_status("processing")
                
                # Execute hierarchical agent teams workflow
                await streaming_graph.ainvoke({
                    "messages": [HumanMessage(content=message)],
                    "metadata": {"conversation_id": conversation_id, "request_id": request_id},
                })
                
                update_request_status("completed")
                logger.info(f"Hierarchical agent workflow completed: {request_id}")
                
            except Exception as e:
                logger.error(f"Hierarchical agent workflow failed [{request_id}]: {e}")
                update_request_status("failed")
                
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                await queue.put(json.dumps(error_data, ensure_ascii=False))
            finally:
                await queue.put("[DONE]")

        async def event_publisher() -> AsyncGenerator[bytes, None]:
            """Stream hierarchical agent execution events to client."""
            asyncio.create_task(producer())
            while True:
                try:
                    chunk = await queue.get()
                    if chunk == "[DONE]":
                        yield b"data: [DONE]\n\n"
                        break
                    yield f"data: {chunk}\n\n".encode("utf-8")
                except Exception as e:
                    logger.error(f"Streaming error [{request_id}]: {e}")
                    error_event = json.dumps({
                        "type": "stream_error",
                        "error": str(e)
                    })
                    yield f"data: {error_event}\n\n".encode("utf-8")
                    break

        return StreamingResponse(
            event_publisher(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id or "unknown"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize hierarchical agent workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Hierarchical agent system initialization failed: {str(e)}"
        )
