from __future__ import annotations

import os
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI

# Our simple state: messages history and optional metadata
class ChatState(dict):
    messages: list[BaseMessage]
    metadata: Dict[str, Any]


def build_graph(
    api_key: str,
    base_url: str,
    model: str,
    callback_handler,
):
    """
    Build a simple LangGraph where a single node calls the model with streaming.
    The provided callback handler will receive tokens as they are generated.
    """

    async def call_model(state: ChatState) -> ChatState:
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.7,
            streaming=True,
            callbacks=[callback_handler],
        )
        # Using async invoke ensures async callbacks (token streaming) are used
        response = await llm.ainvoke(state["messages"])
        final_text = response.content if hasattr(response, "content") else ""
        return {
            "messages": state["messages"] + [AIMessage(content=final_text)],
            "metadata": state.get("metadata", {}),
        }

    graph = StateGraph(ChatState)
    graph.add_node("llm", call_model)
    graph.set_entry_point("llm")
    graph.add_edge("llm", END)

    return graph.compile()
