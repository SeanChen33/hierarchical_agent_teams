from __future__ import annotations

from typing import Literal, Tuple

from langchain_core.messages import HumanMessage
from utils.react_agent_factory import create_react_agent
from langgraph.types import Command

from research_teams.research_team_tools import search_web, scrape_webpages
from utils.supervisor import make_team_supervisor_node, State
from utils.context import current_team, current_node


def build_research_team(llm) -> Tuple:
	# ReAct-style tools-based agents
	search_agent = create_react_agent(llm, tools=[search_web])

	def search_node(state: State) -> Command[Literal["supervisor"]]:
		token = current_team.set("research_team")
		token_node = current_node.set("search")
		try:
			result = search_agent.invoke(state)
			return Command(
				update={
					"messages": [
						HumanMessage(content=result["messages"][-1].content, name="search")
					]
				},
				goto="supervisor",
			)
		finally:
			current_node.reset(token_node)
			current_team.reset(token)
			
	web_scraper_agent = create_react_agent(llm, tools=[scrape_webpages])
	
	def web_scraper_node(state: State) -> Command[Literal["supervisor"]]:
		token = current_team.set("research_team")
		token_node = current_node.set("web_scraper")
		try:
			result = web_scraper_agent.invoke(state)
			return Command(
				update={
					"messages": [
						HumanMessage(content=result["messages"][-1].content, name="web_scraper")
					]
				},
				goto="supervisor",
			)
		finally:
			current_node.reset(token_node)
			current_team.reset(token)

	research_supervisor_node = make_team_supervisor_node(llm, ["search", "web_scraper"], "Research Team")

	return research_supervisor_node, search_node, web_scraper_node 