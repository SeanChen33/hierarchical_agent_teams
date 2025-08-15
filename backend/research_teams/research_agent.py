from __future__ import annotations

from typing import Literal, Tuple

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent 
from langgraph.types import Command

from research_team_tools import tavily_tool, scrape_webpages
from backend.utils.supervisor import make_supervisor_node, State


def build_research_team(llm) -> Tuple:
    # ReAct-style tools-based agents
    search_agent = create_react_agent(llm, tools=[tavily_tool])
    web_scraper_agent = create_react_agent(llm, tools=[scrape_webpages])

    def search_node(state: State) -> Command[Literal["supervisor"]]:
        result = search_agent.invoke(state)
        return Command(
            update={
                "messages": [
                    HumanMessage(content=result["messages"][-1].content, name="search")
                ]
            },
            goto="supervisor",
        )

    def web_scraper_node(state: State) -> Command[Literal["supervisor"]]:
        result = web_scraper_agent.invoke(state)
        return Command(
            update={
                "messages": [
                    HumanMessage(content=result["messages"][-1].content, name="web_scraper")
                ]
            },
            goto="supervisor",
        )

    research_supervisor_node = make_supervisor_node(llm, ["search", "web_scraper"])

    return research_supervisor_node, search_node, web_scraper_node 