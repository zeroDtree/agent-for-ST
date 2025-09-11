# Configuration and utils
from utils.monitor import monitor_performance
from utils.history import cleanup_old_messages

# Custom packages
from llms.llm_with_tools import llm_with_tools, create_llm_with_tools
from states.state import State


@monitor_performance
def chatbot(state: State):
    """Main chatbot function with performance monitoring"""
    state["messages"] = cleanup_old_messages(state["messages"])
    messages = state["messages"]
    
    # Check if we should use a dynamic LLM instance
    if hasattr(state, 'use_dynamic_llm') and state.get('use_dynamic_llm', False):
        llm_instance = create_llm_with_tools()
    else:
        llm_instance = llm_with_tools
    
    response = llm_instance.invoke(messages)
    return {"messages": [response]}
