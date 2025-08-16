from utils.supervisor import State
from langgraph.graph import StateGraph, START
from research_teams.research_agent import build_research_team


def build_research_graph(llm):
	research_supervisor_node, search_node, web_scraper_node = build_research_team(llm)
	builder = StateGraph(State)
	builder.add_node("supervisor", research_supervisor_node)
	builder.add_node("search", search_node)
	builder.add_node("web_scraper", web_scraper_node)
	builder.add_edge(START, "supervisor")
	return builder.compile()