from __future__ import annotations
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Optional, Callable
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import AnyMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import os


class AgentState(TypedDict):
	messages: Annotated[Sequence[BaseMessage], add_messages]


def create_react_agent(
	model: Any,
	tools: Iterable[BaseTool],
	prompt: Optional[str] = None,
):
	tools = list(tools)
	tools_by_name: Dict[str, BaseTool] = {t.name: t for t in tools if getattr(t, "name", None)}

	# Enhanced DashScope detection
	bailian_base = os.getenv("BAILIAN_BASE_URL", "").lower()
	model_base = str(getattr(model, "base_url", "")).lower()
	model_config = getattr(model, "_default_params", {})
	model_name = str(model_config.get("model", "")).lower()
	
	is_dashscope = (
		"dashscope" in bailian_base or 
		"dashscope" in model_base or 
		"aliyun" in model_base or
		"dashscope" in model_name or
		"qwen" in model_name or
		"moonshot" in model_name
	)
	
	env_disable = os.getenv("DISABLE_TOOL_CALLS", "").lower() in {"1", "true", "yes"}
	env_force = os.getenv("FORCE_TOOL_CALLS", "").lower() in {"1", "true", "yes"}
	enable_tools = (not is_dashscope and not env_disable) or env_force

	# Debug logging (remove in production)
	if os.getenv("DEBUG_TOOLS"):
		print(f"DashScope detection: {is_dashscope}")
		print(f"  bailian_base: {bailian_base}")
		print(f"  model_base: {model_base}")
		print(f"  model_name: {model_name}")
		print(f"  enable_tools: {enable_tools}")

	bound_model = model
	if enable_tools and hasattr(model, "bind_tools") and tools_by_name:
		bound_model = model.bind_tools(list(tools_by_name.values()))

	def call_model(state: AgentState) -> Dict[str, List[AnyMessage]]:
		msgs: List[AnyMessage] = list(state["messages"])  # type: ignore
		if prompt:
			msgs = [SystemMessage(content=prompt), *msgs]
		resp = bound_model.invoke(msgs)
		return {"messages": [resp]}

	def tool_node(state: AgentState) -> Dict[str, List[ToolMessage]]:
		outputs: List[ToolMessage] = []
		last = state["messages"][-1]
		for call in getattr(last, "tool_calls", []) or []:
			name = call.get("name")
			args = call.get("args", {})
			tool = tools_by_name.get(name)
			if tool is None:
				continue
			result = tool.invoke(args)
			outputs.append(ToolMessage(content=str(result), name=name, tool_call_id=call.get("id")))
		return {"messages": outputs}

	def should_continue(state: AgentState) -> str:
		if not enable_tools:
			return "end"
		last = state["messages"][-1]
		return "continue" if getattr(last, "tool_calls", []) else "end"

	workflow = StateGraph(AgentState)
	workflow.add_node("agent", call_model)
	if enable_tools and tools_by_name:
		workflow.add_node("tools", tool_node)
		workflow.set_entry_point("agent")
		workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
		workflow.add_edge("tools", "agent")
	else:
		workflow.set_entry_point("agent")
		workflow.add_edge("agent", END)
	return workflow.compile() 