from typing import Literal, Tuple
from backend.utils.supervisor import State, make_supervisor_node
from langgraph.graph import StateGraph, START
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from research_graph import research_graph
from document_graph import paper_writing_graph

def build_teams_supervisor(llm) -> Tuple:
    teams_supervisor_node = make_supervisor_node(llm, ["research_team", "writing_team"])
    return teams_supervisor_node

def call_research_team(state: State) -> Command[Literal["supervisor"]]:
    response = research_graph.invoke({"messages": state["messages"][-1]})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response["messages"][-1].content, name="research_team"
                )
            ]
        },
        goto="supervisor",
    )


def call_paper_writing_team(state: State) -> Command[Literal["supervisor"]]:
    response = paper_writing_graph.invoke({"messages": state["messages"][-1]})
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response["messages"][-1].content, name="writing_team"
                )
            ]
        },
        goto="supervisor",
    )


# Define the graph.
super_builder = StateGraph(State)
super_builder.add_node("supervisor", build_teams_supervisor)
super_builder.add_node("research_team", call_research_team)
super_builder.add_node("writing_team", call_paper_writing_team)

super_builder.add_edge(START, "supervisor")
super_graph = super_builder.compile()