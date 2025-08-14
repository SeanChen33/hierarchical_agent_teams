from __future__ import annotations

import os
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from service import (
    create_research_team_llm,
    create_authoring_team_llm,
    RESEARCH_SYSTEM_PROMPT,
    AUTHORING_SYSTEM_PROMPT,
    prepend_system,
)

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
    Build a two-stage hierarchical agent team pipeline:
    1) Research team (non-streaming) synthesizes a research brief
    2) Authoring team (streaming) writes the final document (SSE tokens)
    """

    async def research_stage(state: ChatState) -> ChatState:
        research_llm = create_research_team_llm(
            api_key=api_key, base_url=base_url, model=model
        )
        # Prepend research system prompt
        research_messages = prepend_system(RESEARCH_SYSTEM_PROMPT, state["messages"])
        research_response = await research_llm.ainvoke(research_messages)
        research_text = (
            research_response.content if hasattr(research_response, "content") else ""
        )
        # Stash research brief into metadata for the next stage
        new_metadata = dict(state.get("metadata", {}))
        new_metadata["research_brief"] = research_text
        # Also append an AI message with the research summary (not streamed)
        return {
            "messages": state["messages"] + [AIMessage(content=research_text)],
            "metadata": new_metadata,
        }

    async def authoring_stage(state: ChatState) -> ChatState:
        authoring_llm = create_authoring_team_llm(
            api_key=api_key, base_url=base_url, model=model, callbacks=callback_handler
        )
        # Combine authoring system prompt with research brief context
        research_brief = state.get("metadata", {}).get("research_brief", "")
        authoring_system = f"{AUTHORING_SYSTEM_PROMPT}\n\nResearch Brief:\n{research_brief}".strip()
        authoring_messages = prepend_system(authoring_system, state["messages"])
        authoring_response = await authoring_llm.ainvoke(authoring_messages)
        final_text = (
            authoring_response.content if hasattr(authoring_response, "content") else ""
        )
        return {
            "messages": state["messages"] + [AIMessage(content=final_text)],
            "metadata": state.get("metadata", {}),
        }

    graph = StateGraph(ChatState)
    graph.add_node("research", research_stage)
    graph.add_node("author", authoring_stage)
    graph.set_entry_point("research")
    graph.add_edge("research", "author")
    graph.add_edge("author", END)

    return graph.compile()
