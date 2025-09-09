# Configuration and utils
from utils.monitor import monitor_performance
from utils.history import cleanup_old_messages

# Custom packages
from llms.llm_with_tools import llm_with_tools
from states.state import State


@monitor_performance
def chatbot(state: State):
    """Main chatbot function with performance monitoring"""
    state["messages"] = cleanup_old_messages(state["messages"])
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}
