from states import State
from utils.logger import logger
from langchain_core.messages import ToolMessage
from langgraph.types import Command


def get_auto_reject_node(next_node: str):
    def auto_reject_node(state: State):
        return reject_node(state, next_node)

    return auto_reject_node


def reject_node(state: State, next_node: str):
    """Auto reject node - automatically reject commands with explanation"""
    tool_call_message = state["messages"][-1]

    # Extract command information for logging
    command_info = ""
    tool_name = "unknown"
    rejection_reason = "Auto-rejected by system policy"

    if hasattr(tool_call_message, "tool_calls") and tool_call_message.tool_calls:
        tool_call = tool_call_message.tool_calls[0]
        tool_name = tool_call.get("name", "unknown")
        args = tool_call.get("args", {})

        if tool_name == "run_shell_command_popen_tool":
            command_info = args.get("command", "")

            # Get more specific rejection reason
            try:
                from tools.whitelist import get_command_category, get_auto_mode_description
                from config.config import CONFIG

                category = get_command_category(command_info)
                auto_mode = CONFIG.get("auto_mode", "manual")

                if category == "dangerous":
                    rejection_reason = f"Auto-rejected: dangerous command in blacklist (mode: {auto_mode})"
                elif auto_mode == "universal_reject":
                    rejection_reason = f"Auto-rejected: universal reject mode enabled"
                else:
                    rejection_reason = f"Auto-rejected by {auto_mode} mode"

            except ImportError:
                rejection_reason = "Auto-rejected by system policy"
        else:
            command_info = f"{tool_name}: {str(args)}"
            rejection_reason = "Auto-rejected: tool requires confirmation but auto mode rejects"

    logger.info(f"Auto-rejected command: {command_info}, reason: {rejection_reason}")

    # Create rejection messages for all tool calls
    tool_messages = []
    for tool_call in tool_call_message.tool_calls:
        tool_message = ToolMessage(content=f"🚫 {rejection_reason}", tool_call_id=tool_call["id"])
        tool_messages.append(tool_message)

    # Return to chatbot with rejection messages
    return Command(goto=next_node, update={"messages": tool_messages})
