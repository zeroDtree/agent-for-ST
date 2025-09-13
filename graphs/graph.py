from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode

from edges import chatbot_route
from nodes import chatbot, get_auto_reject_node, get_human_confirm_node
from states import State

# Custom packages
from tools import ALL_TOOLS


def create_graph(tools=None, checkpointer=None, web_mode=False, need_memory=False):
    """Create graph structure with dependency injection support"""
    if tools is None:
        tools = ALL_TOOLS

    if checkpointer is None:
        checkpointer = InMemorySaver() if need_memory else None

    tool_node = ToolNode(tools=tools)
    graph_builder = StateGraph(State)

    graph_builder.add_node("my_tools", tool_node)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node(
        "human_confirm",
        get_human_confirm_node(next_node_for_yes="my_tools", next_node_for_no="chatbot", web_mode=web_mode),
    )
    graph_builder.add_node("auto_reject", get_auto_reject_node(next_node="chatbot"))
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("my_tools", "chatbot")
    graph_builder.add_edge("auto_reject", "chatbot")

    graph_builder.add_conditional_edges(
        "chatbot",
        chatbot_route,
    )

    return graph_builder.compile(checkpointer=checkpointer)
