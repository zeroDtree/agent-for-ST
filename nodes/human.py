from langgraph.graph import START, END
from langgraph.types import Command
from states.state import State
from langchain_core.messages import ToolMessage
import threading
import time
from utils.logger import logger


def get_human_confirm_node(next_node_for_yes: str, next_node_for_no: str, web_mode=False):
    def human_confirm(state: State):
        tool_call_message = state["messages"][-1]
        nonlocal next_node_for_yes
        nonlocal next_node_for_no
        
        if web_mode:
            return web_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)
        else:
            return console_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)

    return human_confirm


def console_confirm(state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
    """Console mode confirmation"""
    print(tool_call_message)
    human_str = input(f"About to execute {tool_call_message.content},\nDo you want to proceed? (yes/no): ")
    if human_str in ["y", "Y", "yes", "Yes", "YES"]:
        return Command(goto=next_node_for_yes)
    else:
        # When user rejects, add tool response message indicating rejection
        messages = state["messages"]
        tool_messages = []
        for tool_call in tool_call_message.tool_calls:
            tool_message = ToolMessage(
                content="User rejected execution of this tool call",
                tool_call_id=tool_call["id"]
            )
            tool_messages.append(tool_message)
        
        return Command(goto=next_node_for_no, update={"messages": tool_messages})


def web_confirm(state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
    """Web mode confirmation - interact with frontend through API interface"""
    # Get global pending_confirmations (needs to be defined in web_server)
    try:
        # Dynamic import to avoid circular import
        import web_server
        pending_confirmations = web_server.pending_confirmations
    except ImportError:
        logger.error("Web mode confirmation requires web_server module")
        return console_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)
    
    # Extract command information
    command_info = ""
    tool_name = "unknown"
    
    if hasattr(tool_call_message, "tool_calls") and tool_call_message.tool_calls:
        tool_call = tool_call_message.tool_calls[0]
        tool_name = tool_call.get("name", "unknown")
        args = tool_call.get("args", {})
        
        if tool_name == "run_shell_command_popen_tool":
            command_info = args.get("command", "")
        else:
            command_info = f"{tool_name}: {str(args)}"
    
    # Generate session ID (simplified here, can be obtained from request in actual application)
    session_id = getattr(state, 'session_id', 'default')
    
    # Create confirmation event
    confirmation_event = threading.Event()
    confirmation_result = {"confirmed": False}
    
    def confirmation_callback(confirmed: bool):
        confirmation_result["confirmed"] = confirmed
        confirmation_event.set()
    
    # Add to pending confirmation list
    pending_confirmations[session_id] = {
        "command": command_info,
        "tool_name": tool_name,
        "callback": confirmation_callback
    }
    
    # Push confirmation request through SSE
    try:
        web_server.send_sse_event(session_id, {
            "type": "confirmation_request",
            "command": command_info,
            "tool_name": tool_name,
            "session_id": session_id
        })
        logger.info(f"Confirmation request pushed via SSE: {command_info}")
    except Exception as e:
        logger.warning(f"SSE push failed, will rely on polling mechanism: {e}")
    
    logger.info(f"Waiting for web frontend to confirm command: {command_info}")
    
    # Wait for frontend confirmation (with timeout)
    timeout = 300  # 5 minute timeout
    if confirmation_event.wait(timeout):
        # User has made a choice
        if confirmation_result["confirmed"]:
            logger.info(f"User confirmed command execution: {command_info}")
            return Command(goto=next_node_for_yes)
        else:
            logger.info(f"User rejected command execution: {command_info}")
            # Add rejection message
            tool_messages = []
            for tool_call in tool_call_message.tool_calls:
                tool_message = ToolMessage(
                    content="User rejected execution of this tool call",
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)
            
            return Command(goto=next_node_for_no, update={"messages": tool_messages})
    else:
        # Timeout handling
        logger.warning(f"Command confirmation timeout: {command_info}")
        # Clean up pending confirmation status
        if session_id in pending_confirmations:
            del pending_confirmations[session_id]
        
        # Add timeout message
        tool_messages = []
        for tool_call in tool_call_message.tool_calls:
            tool_message = ToolMessage(
                content="Command confirmation timeout, automatically rejected execution",
                tool_call_id=tool_call["id"]
            )
            tool_messages.append(tool_message)
        
        return Command(goto=next_node_for_no, update={"messages": tool_messages})
