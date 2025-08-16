from __future__ import annotations

from typing import Literal, Tuple

from langchain_core.messages import HumanMessage
from utils.react_agent_factory import create_react_agent
from langgraph.types import Command

from document_teams.document_team_tools import (
	create_outline,
	read_document,
	write_document,
	edit_document,
	python_repl_tool,
)
from utils.supervisor import make_team_supervisor_node, State
from utils.context import current_team, current_node


def build_document_team(llm) -> Tuple:
	
	doc_writer_agent = create_react_agent(
		llm,
		tools=[write_document, edit_document, read_document],
		prompt=(
			"You can read, write and edit documents based on note-taker's outlines. "
			"Don't ask follow-up questions."
		),
	)

	def doc_writing_node(state: State) -> Command[Literal["supervisor"]]:
		# Don't override team context if it's already set to "final"
		current_team_value = current_team.get("")
		if current_team_value != "final":
			token = current_team.set("document_team")
		else:
			token = None
		token_node = current_node.set("doc_writer")
		try:
			result = doc_writer_agent.invoke(state)
			return Command(
				update={
					"messages": [
						HumanMessage(content=result["messages"][-1].content, name="doc_writer")
					]
				},
				goto="supervisor",
			)
		finally:
			current_node.reset(token_node)
			if token:
				current_team.reset(token)

	note_taking_agent = create_react_agent(
		llm,
		tools=[create_outline, read_document],
		prompt=(
			"You can read documents and create outlines for the document writer. "
			"Don't ask follow-up questions."
		),
	)

	def note_taking_node(state: State) -> Command[Literal["supervisor"]]:
		# Don't override team context if it's already set to "final"
		current_team_value = current_team.get("")
		if current_team_value != "final":
			token = current_team.set("document_team")
		else:
			token = None
		token_node = current_node.set("note_taker")
		try:
			result = note_taking_agent.invoke(state)
			return Command(
				update={
					"messages": [
						HumanMessage(content=result["messages"][-1].content, name="note_taker")
					]
				},
				goto="supervisor",
			)
		finally:
			current_node.reset(token_node)
			if token:
				current_team.reset(token)

	chart_generating_agent = create_react_agent(
		llm, tools=[read_document, python_repl_tool]
	)

	def chart_generating_node(state: State) -> Command[Literal["supervisor"]]:
		# Don't override team context if it's already set to "final"
		current_team_value = current_team.get("")
		if current_team_value != "final":
			token = current_team.set("document_team")
		else:
			token = None
		token_node = current_node.set("chart_generator")
		try:
			result = chart_generating_agent.invoke(state)
			return Command(
				update={
					"messages": [
						HumanMessage(
							content=result["messages"][-1].content, name="chart_generator"
						)
					]
				},
				goto="supervisor",
			)
		finally:
			current_node.reset(token_node)
			if token:
				current_team.reset(token)

	doc_writing_supervisor_node = make_team_supervisor_node(
		llm, ["doc_writer", "note_taker", "chart_generator"], "Document Team"
	)

	return (
		doc_writing_supervisor_node,
		doc_writing_node,
		note_taking_node,
		chart_generating_node,
	) 