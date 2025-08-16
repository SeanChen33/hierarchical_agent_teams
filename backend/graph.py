from typing import Tuple
from utils.supervisor import State, make_supervisor_node
from langgraph.graph import StateGraph, START
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from research_teams.research_graph import build_research_graph
from document_teams.document_graph import build_document_graph
from utils.context import current_team
import logging

logger = logging.getLogger(__name__)


def build_super_graph(llm):
	"""Build hierarchical agent teams super graph with intelligent routing.
	
	Implements three-layer architecture:
	1. Super Graph (this) - Top-level task coordinator
	2. Team Graphs - Specialized teams (Research/Document)
	3. Individual Agents - Tool-based reactive agents
	"""
	logger.info("Building hierarchical agent teams super graph")
	
	# Create intelligent supervisor with enhanced routing
	teams_supervisor_node = make_supervisor_node(llm, ["research_team", "writing_team"])

	# Build specialized team graphs
	research_graph = build_research_graph(llm)
	paper_writing_graph = build_document_graph(llm)

	def call_research_team(state: State) -> Command[str]:
		"""Execute research team with context tracking and error handling."""
		try:
			# Set context for research phase
			token = current_team.set("research_team")
			
			logger.info("Starting research team execution")
			
			# Execute research team graph
			resp = research_graph.invoke({
				"messages": state["messages"],
			})
			
			last = resp["messages"][-1]
			
			logger.info("Research team completed successfully")
			
			return Command(
				update={
					"messages": [HumanMessage(content=last.content, name="research_team")],
					"research_done": True
				},
				goto="supervisor",
			)
			
		except Exception as e:
			logger.error(f"Research team execution failed: {e}")
			
			# Return error message but continue workflow
			return Command(
				update={
					"messages": [AIMessage(content=f"研究阶段遇到问题：{str(e)}，将直接进入文档生成阶段。")],
					"research_done": True
				},
				goto="supervisor",
			)
		finally:
			current_team.reset(token)

	def call_writing_team(state: State) -> Command[str]:
		"""Execute document team as final stage with comprehensive output."""
		try:
			# Mark as final team for output filtering
			token = current_team.set("final")
			
			logger.info("Starting writing team execution")
			
			# Execute document team graph
			resp = paper_writing_graph.invoke({
				"messages": state["messages"],
			})
			
			last = resp["messages"][-1]
			
			logger.info("Writing team completed successfully")
			
			return Command(
				update={
					"messages": [HumanMessage(content=last.content, name="writing_team")],
					"writing_done": True
				},
				goto="supervisor",
			)
			
		except Exception as e:
			logger.error(f"Writing team execution failed: {e}")
			
			# Return error but mark as complete
			return Command(
				update={
					"messages": [AIMessage(content=f"抱歉，文档生成阶段遇到问题：{str(e)}")],
					"writing_done": True
				},
				goto="supervisor",
			)
		finally:
			current_team.reset(token)

	# Build hierarchical super graph
	master = StateGraph(State)
	master.add_node("supervisor", teams_supervisor_node)
	master.add_node("research_team", call_research_team)
	master.add_node("writing_team", call_writing_team)
	
	# Set entry point to supervisor for intelligent routing
	master.add_edge(START, "supervisor")
	
	logger.info("Hierarchical agent teams super graph built successfully")
	return master.compile()