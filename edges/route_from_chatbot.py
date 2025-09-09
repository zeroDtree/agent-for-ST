from langgraph.graph import END

# Configuration and utils
from config.config import CONFIG, TOOL_SECURITY_CONFIG
from utils.logger import logger
from utils.cache import cached_is_safe_command
from states.state import State


def chatbot_route(state: State):
    """Routing function to handle tool calls"""
    try:
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")

        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            # Get tool categories from config file
            safe_tools = TOOL_SECURITY_CONFIG["safe_tools"]
            shell_tools = TOOL_SECURITY_CONFIG["shell_tools"]
            confirm_required_tools = TOOL_SECURITY_CONFIG["confirm_required_tools"]

            # Log tool call information
            tool_names = [tool_call.get("name", "unknown") for tool_call in ai_message.tool_calls]
            logger.info(f"Tool calls detected: {', '.join(tool_names)}")

            for tool_call in ai_message.tool_calls:
                tool_name = tool_call.get("name", "")
                args = tool_call.get("args", {})

                # Handle safe tools (execute directly)
                if tool_name in safe_tools:
                    logger.info(f"Safe tool call: {tool_name}")
                    print(f"🟢 Safe tool, executing directly: {tool_name}")
                    return "my_tools"

                # Handle tools requiring confirmation
                elif tool_name in confirm_required_tools:
                    logger.info(f"Tool requiring confirmation: {tool_name}")

                    # Check auto mode for confirmation-required tools
                    auto_mode = CONFIG.get("auto_mode", "manual")
                    if auto_mode == "universal_reject":
                        print(f"🚫 Auto-rejected: {tool_name} (universal reject mode)")
                        logger.info(f"Auto-rejected tool: {tool_name}, mode: universal_reject")
                        return "auto_reject"
                    elif auto_mode == "universal_accept":
                        print(f"🤖 Auto-approved: {tool_name} (universal accept mode)")
                        logger.info(f"Auto-approved tool: {tool_name}, mode: universal_accept")
                        return "my_tools"
                    else:
                        print(f"⚠️ Tool requires confirmation: {tool_name}")
                        return "human_confirm"

                # Handle shell command tools
                elif tool_name in shell_tools:
                    command = args.get("command", "")
                    logger.info(f"Shell command tool call: {tool_name}, command: {command}")

                    # Check auto mode first
                    auto_mode = CONFIG.get("auto_mode", "manual")

                    # Always check if command is whitelisted first (safe commands execute regardless of auto mode)
                    if CONFIG.get("restricted_mode", False):
                        try:
                            from tools.whitelist import is_safe_command_with_restrictions

                            is_whitelisted = is_safe_command_with_restrictions(command)
                        except ImportError:
                            is_whitelisted = cached_is_safe_command(command)
                    else:
                        is_whitelisted = cached_is_safe_command(command)

                    if is_whitelisted:
                        print(f"🟢 Whitelisted command, executing directly: {command}")
                        return "my_tools"

                    # For non-whitelisted commands, check auto mode
                    if auto_mode != "manual":
                        try:
                            from tools.whitelist import should_auto_approve_command, get_auto_mode_description

                            should_approve, reason = should_auto_approve_command(command)
                            if should_approve:
                                print(f"🤖 {reason}: {command}")
                                logger.info(f"Auto-approved command: {command}, reason: {reason}")
                                return "my_tools"
                            else:
                                # Check if it's an auto-rejection
                                if "Auto-rejected" in reason:
                                    print(f"🚫 {reason}: {command}")
                                    logger.info(f"Auto-rejected command: {command}, reason: {reason}")
                                    # Return auto_reject to provide proper feedback
                                    return "auto_reject"
                                else:
                                    print(f"⚠️ {reason}: {command}")
                                    return "human_confirm"
                        except ImportError:
                            print(f"⚠️ Auto mode not available, falling back to manual mode")
                            # Fall through to manual mode logic

                    # Manual mode or fallback logic
                    if CONFIG.get("restricted_mode", False):
                        # In restricted mode, use enhanced validation
                        try:
                            from tools.whitelist import is_safe_command_with_restrictions

                            if is_safe_command_with_restrictions(command):
                                print(f"🟢 Safe command (restricted mode), executing: {command}")
                                return "my_tools"
                            else:
                                print(f"🚫 Command blocked in restricted mode: {command}")
                                return "human_confirm"
                        except ImportError:
                            # Fallback to regular check
                            if cached_is_safe_command(command):
                                print(f"🟢 Whitelisted command, executing directly: {command}")
                                return "my_tools"
                            else:
                                print(f"⚠️ Non-whitelisted command, requires confirmation: {command}")
                                return "human_confirm"
                    else:
                        # Normal mode, use cached whitelist check
                        print(f"⚠️ Non-whitelisted command, requires confirmation: {command}")
                        return "human_confirm"

                # Other tools require confirmation by default
                else:
                    logger.warning(f"Unknown tool call: {tool_name}")

                    # Check auto mode for unknown tools
                    auto_mode = CONFIG.get("auto_mode", "manual")
                    if auto_mode == "universal_reject":
                        print(f"🚫 Auto-rejected: {tool_name} (universal reject mode)")
                        logger.info(f"Auto-rejected unknown tool: {tool_name}, mode: universal_reject")
                        return "auto_reject"
                    elif auto_mode == "universal_accept":
                        print(f"🤖 Auto-approved: {tool_name} (universal accept mode)")
                        logger.info(f"Auto-approved unknown tool: {tool_name}, mode: universal_accept")
                        return "my_tools"
                    else:
                        print(f"⚠️ Unknown tool, requires confirmation: {tool_name}")
                        return "human_confirm"

        return END
    except Exception as e:
        logger.error(f"Routing function execution error: {e}")
        print(f"🚫 Routing processing error: {e}")
        return END
