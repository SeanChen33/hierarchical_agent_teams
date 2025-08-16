from utils.supervisor import State
from langgraph.graph import StateGraph, START
from document_teams.document_agent import build_document_team


def build_document_graph(llm):
	builder = StateGraph(State)
	doc_writing_supervisor_node, doc_writing_node, note_taking_node, chart_generating_node = build_document_team(llm)
	builder.add_node("supervisor", doc_writing_supervisor_node)
	builder.add_node("doc_writer", doc_writing_node)
	builder.add_node("note_taker", note_taking_node)
	builder.add_node("chart_generator", chart_generating_node)
	builder.add_edge(START, "supervisor")
	return builder.compile()