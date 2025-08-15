from __future__ import annotations

from typing import Literal, Tuple

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from document_team_tools import (
	create_outline,
	read_document,
	write_document,
	edit_document,
	python_repl_tool,
)
from backend.utils.supervisor import make_supervisor_node, State


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
		result = doc_writer_agent.invoke(state)
		return Command(
			update={
				"messages": [
					HumanMessage(content=result["messages"][-1].content, name="doc_writer")
				]
			},
			goto="supervisor",
		)

	note_taking_agent = create_react_agent(
		llm,
		tools=[create_outline, read_document],
		prompt=(
			"You can read documents and create outlines for the document writer. "
			"Don't ask follow-up questions."
		),
	)

	def note_taking_node(state: State) -> Command[Literal["supervisor"]]:
		result = note_taking_agent.invoke(state)
		return Command(
			update={
				"messages": [
					HumanMessage(content=result["messages"][-1].content, name="note_taker")
				]
			},
			goto="supervisor",
		)

	chart_generating_agent = create_react_agent(
		llm, tools=[read_document, python_repl_tool]
	)

	def chart_generating_node(state: State) -> Command[Literal["supervisor"]]:
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

	doc_writing_supervisor_node = make_supervisor_node(
		llm, ["doc_writer", "note_taker", "chart_generator"]
	)

	return (
		doc_writing_supervisor_node,
		doc_writing_node,
		note_taking_node,
		chart_generating_node,
	) 