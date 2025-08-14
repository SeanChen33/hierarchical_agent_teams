from __future__ import annotations

from typing import Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage


RESEARCH_SYSTEM_PROMPT = (
    "You are the Research Lead coordinating a small research team. "
    "Given the user's request, you will plan and synthesize concise, factual findings. "
    "Do not fabricate citations. If you are uncertain, state the uncertainty. "
    "Output a structured, markdown-formatted brief with sections: \n"
    "1) Objective\n2) Key Findings\n3) Risks & Unknowns\n4) Sources or How-to-verify"
)


AUTHORING_SYSTEM_PROMPT = (
    "You are the Document Authoring Lead supervising an authoring team. "
    "Use the provided research summary to draft a clear, well-structured document for the user. "
    "Prefer markdown with headings, bullet lists, and code blocks when helpful. "
    "Avoid repeating the entire prompt; focus on delivering the final document."
)


def create_research_team_llm(*, api_key: str, base_url: str, model: str) -> ChatOpenAI:
    """Create a research team LLM client.

    - Non-streaming: keep research silent in SSE.
    - No callbacks: we do not forward intermediate tokens.
    """
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.3,
        streaming=False,
        callbacks=None,
    )


def create_authoring_team_llm(
    *, api_key: str, base_url: str, model: str, callbacks: Any
) -> ChatOpenAI:
    """Create a document authoring team LLM client.

    - Streaming enabled with provided callbacks (SSE pipeline).
    """
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.7,
        streaming=True,
        callbacks=[callbacks] if callbacks else None,
    )


def prepend_system(message: str, messages: List[BaseMessage]) -> List[BaseMessage]:
    return [SystemMessage(content=message), *messages]
