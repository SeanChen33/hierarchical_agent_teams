from typing import List, Literal
import json
import logging
from langchain_core.language_models.chat_models import BaseChatModel  # type: ignore
from langgraph.graph import MessagesState, END  # type: ignore
from langgraph.types import Command  # type: ignore
from .context import current_team, current_node

logger = logging.getLogger(__name__)


class State(MessagesState):
	"""Enhanced state for hierarchical agent teams."""
	# Workflow progress tracking
	research_done: bool  # type: ignore[assignment]
	writing_done: bool  # type: ignore[assignment]
	next: str
	
	# Team coordination metadata
	current_team: str = ""  # type: ignore[assignment]
	task_complexity: str = ""  # type: ignore[assignment]
	task_priority: str = "normal"  # type: ignore[assignment]


def make_team_supervisor_node(llm: BaseChatModel, members: List[str], team_name: str):
	"""Create intelligent team supervisor with hierarchical coordination.
	
	This supervisor implements the second layer of hierarchical agent teams:
	- Manages internal agent coordination
	- Provides intelligent task delegation
	- Ensures quality outputs for upper-level supervisor
	- Handles error recovery and fallback strategies
	"""
	options = ["COMPLETE"] + members
	system_prompt = (
		f"You are an intelligent {team_name} supervisor in a hierarchical agent system. "
		f"Managing agents: {members}. Your core responsibilities:\n"
		"1. INTELLIGENT COORDINATION: Analyze tasks and delegate to appropriate agents\n"
		"2. QUALITY ASSURANCE: Ensure comprehensive, professional outputs\n"
		"3. WORKFLOW OPTIMIZATION: Coordinate agent sequences for maximum efficiency\n"
		"4. STRATEGIC OVERSIGHT: Provide synthesized results suitable for higher-level decision making\n\n"
		"Decision Rules:\n"
		"- Route complex tasks requiring specific expertise to specialized agents\n"
		"- Coordinate multiple agents for comprehensive coverage\n"
		"- Synthesize agent outputs into coherent team deliverables\n"
		"- Complete when team objectives are fully accomplished\n\n"
		"Respond in JSON format: {\"next\": \"agent_name\"} or {\"next\": \"COMPLETE\"}"
	)

	def team_supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
		"""Enhanced team supervisor with intelligent coordination and quality control."""
		messages = state["messages"]
		
		# Set team context
		team_token = current_team.set(team_name.lower().replace(" ", "_"))
		node_token = current_node.set("supervisor")
		
		try:
			# Track team activation
			logger.info(f"Team supervisor started: {team_name}")
			
			# Analyze agent contributions
			agent_responses = []
			agent_work_summary = {}
			
			for msg in messages[1:]:  # Skip initial user message
				if hasattr(msg, 'name') and msg.name in members:
					agent_responses.append(f"{msg.name}: {msg.content}")
					agent_work_summary[msg.name] = len(msg.content)
			
			# Check if team has sufficient work completed
			if len(agent_responses) >= 1:
				return _generate_team_response(
					llm, team_name, messages, agent_responses, agent_work_summary
				)
			
			# Route to next agent using intelligent decision making
			return _route_to_next_agent(
				llm, system_prompt, members, messages, team_name
			)
			
		except Exception as e:
			logger.error(f"Team supervisor error in {team_name}: {e}")
			# Fallback to first available agent
			return Command(goto=members[0] if members else END, update={"next": members[0] if members else "__end__"})
			
		finally:
			current_node.reset(node_token)
			current_team.reset(team_token)

	return team_supervisor_node


def _generate_team_response(llm, team_name: str, messages, agent_responses, agent_work_summary):
	"""Generate comprehensive team response based on agent work."""
	user_msg = messages[0].content if messages else ""
	
	# Check if this is the final team
	is_final_team = current_team.get("") == "final"
	
	if is_final_team:
		# Generate comprehensive final response for user
		if "document" in team_name.lower() or "writing" in team_name.lower():
			final_prompt = f"""As the document team supervisor in a hierarchical agent system, provide the FINAL deliverable for: "{user_msg}"

Agent Work Completed:
{chr(10).join(agent_responses)}

Agent Performance Summary: {agent_work_summary}

Generate a comprehensive, polished final deliverable that:
1. Synthesizes all agent contributions professionally
2. Provides complete coverage of the user's request
3. Maintains high quality standards
4. Is ready for immediate user consumption

This is the FINAL output that will be presented to the user."""
		else:
			final_prompt = f"""As the {team_name} supervisor, provide comprehensive final response to: "{user_msg}"

Team Work Completed:
{chr(10).join(agent_responses)}

Generate a complete, professional response addressing the user's request."""
	else:
		# For intermediate teams, just complete without generating visible output
		logger.info(f"Team {team_name} completed work")

		return Command(
			update={},
			goto=END
		)
	
	try:
		final_response = llm.invoke([{"role": "system", "content": final_prompt}])
		from langchain_core.messages import AIMessage
		
		logger.info(f"Team {team_name} generated final response")
		
		return Command(
			update={"messages": [AIMessage(content=final_response.content)]},
			goto=END
		)
	except Exception as e:
		logger.error(f"Failed to generate team response for {team_name}: {e}")
		# Fallback to last agent response
		if agent_responses:
			last_response = agent_responses[-1].split(": ", 1)[-1]
			from langchain_core.messages import AIMessage
			return Command(
				update={"messages": [AIMessage(content=last_response)]},
				goto=END
			)
		return Command(goto=END)


def _route_to_next_agent(llm, system_prompt: str, members: List[str], messages, team_name: str):
	"""Intelligent routing to next agent based on task analysis."""
	# Modify system prompt to request internal decision only
	internal_prompt = system_prompt.replace(
		"Respond in JSON format: {\"next\": \"agent_name\"} or {\"next\": \"COMPLETE\"}",
		"Analyze the task and decide which agent should handle it next. "
		"Consider the task complexity and agent specializations. "
		"Respond with a JSON object containing the agent name (one of: " + ", ".join(members) + ") or COMPLETE."
	)
	
	routing_messages = [
		{"role": "system", "content": internal_prompt},
	] + messages
	
	try:
		# Use simple text response and parse (more reliable)
		response = llm.invoke(routing_messages)
		content = response.content.strip().lower()

		# Simple keyword matching for agent selection
		goto = "COMPLETE"
		for member in members:
			if member.lower() in content:
				goto = member
				break

		if goto == "COMPLETE" and members:
			# Default to first agent if no clear decision
			goto = members[0]

	except Exception as e:
		logger.warning(f"Routing decision failed for {team_name}, using fallback: {e}")
		goto = members[0] if members else "COMPLETE"

	if goto == "COMPLETE":
		goto = END
	
	# Log routing decision
	logger.info(f"Routing {team_name} to: {goto}")
	
	return Command(goto=goto, update={"next": goto})


def make_supervisor_node(llm: BaseChatModel, members: List[str]):
	"""Create a router that chooses among provided members or COMPLETE.

	Intelligently routes based on task complexity:
	- Simple document tasks → writing_team directly
	- Complex tasks → research_team first, then writing_team
	- Handles sequential workflow properly
	"""
	options = ["COMPLETE"] + members
	
	def analyze_task_complexity(messages: List) -> str:
		"""Analyze if task needs research or can go directly to document team."""
		if not messages:
			return "research_team"

		user_message = messages[0].content.lower() if messages else ""

		# Keywords indicating simple document tasks
		simple_doc_keywords = [
			"整理", "总结", "撰写", "编写", "文档", "报告", "记录", "笔记",
			"organize", "summarize", "write", "document", "report", "note",
			"format", "create document", "draft"
		]

		# Keywords indicating research is needed
		research_keywords = [
			"搜索", "查找", "调研", "分析", "研究", "收集信息", "最新",
			"search", "find", "research", "analyze", "investigate", "gather", "latest",
			"compare", "评估", "市场", "趋势", "数据"
		]

		# Check for research indicators
		for keyword in research_keywords:
			if keyword in user_message:
				return "research_team"

		# Check for simple document tasks
		for keyword in simple_doc_keywords:
			if keyword in user_message:
				return "writing_team"

		# Default to research for complex/ambiguous tasks
		return "research_team"

	system_prompt = (
		"You are a top-level supervisor managing research and document teams. "
		f"Available teams: {members}. "
		"Route tasks intelligently:\n"
		"1. Simple document/writing tasks → writing_team directly\n"
		"2. Research/information gathering tasks → research_team first\n"
		"3. After research_team completes → writing_team for documentation\n"
		"4. After writing_team completes → COMPLETE\n"
		"Respond with a JSON object containing the next team."
	)

	def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
		"""Intelligent task router."""
		messages = state["messages"]
		
		# Track team responses
		research_completed = False
		writing_completed = False
		
		for msg in messages[1:]:  # Skip initial user message
			if hasattr(msg, 'name'):
				if msg.name == 'research_team':
					research_completed = True
				elif msg.name == 'writing_team':
					writing_completed = True
		
		# Decision logic based on workflow state
		if writing_completed:
			# Writing team has provided final output
			goto = END
		elif research_completed and not writing_completed:
			# Research done, now need writing
			goto = "writing_team"
		elif not research_completed and not writing_completed:
			# Initial routing - analyze task complexity
			task_route = analyze_task_complexity(messages)
			goto = task_route
		else:
			# Fallback
			goto = END
		
		# Use LLM for complex routing decisions when needed
		if goto not in [END, "writing_team"] and len(messages) > 1:
			routing_messages = [
				{"role": "system", "content": system_prompt},
			] + messages
			try:
				response = llm.invoke(routing_messages)
				content = response.content.strip().lower()
				# Simple keyword matching for team selection
				for member in members:
					if member.lower() in content:
						goto = member
						break
			except Exception:
				pass  # Keep the analyzed route
		
		if goto == "COMPLETE":
			goto = END
		
		# Log routing decision  
		logger.info(f"Super supervisor routing to: {goto}")
		
		return Command(goto=goto, update={"next": goto})

	return supervisor_node