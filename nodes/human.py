from langchain_core.messages import ToolMessage
from langgraph.types import Command

from config.config import CONFIG
from interfaces import web_confirmation_interface
from states.state import State
from utils.logger import get_and_create_new_log_dir, get_logger

log_dir = get_and_create_new_log_dir(root=CONFIG["log_dir"], prefix="", suffix="", strftime_format="%Y%m%d")
logger = get_logger(name=__name__, log_dir=log_dir)


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
                tool_call_id=tool_call["id"],
            )
            tool_messages.append(tool_message)

        return Command(goto=next_node_for_no, update={"messages": tool_messages})


def web_confirm(state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
    """Web mode confirmation - interact with frontend through API interface"""
    # Check if web interface is available
    if not web_confirmation_interface.is_available():
        logger.error("Web confirmation interface not available - falling back to console mode")
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

    # Generate session ID (simplified here, can be obtained from request in
    # actual application)
    session_id = getattr(state, "session_id", "default")

    # Request confirmation through web interface
    confirmed = web_confirmation_interface.request_confirmation(
        # 5 minute timeout
        session_id=session_id,
        command_info=command_info,
        tool_name=tool_name,
        timeout=300,
    )

    if confirmed:
        logger.info(f"User confirmed command execution: {command_info}")
        return Command(goto=next_node_for_yes)
    else:
        logger.info(f"User rejected or timeout for command execution: {command_info}")
        # Add rejection/timeout message
        tool_messages = []
        for tool_call in tool_call_message.tool_calls:
            tool_message = ToolMessage(
                content="User rejected execution or confirmation timeout occurred",
                tool_call_id=tool_call["id"],
            )
            tool_messages.append(tool_message)

        return Command(goto=next_node_for_no, update={"messages": tool_messages})
