# offical package
from langchain_core.messages import HumanMessage
import argparse
import os


# Custom packages
from utils.preset import preset_messages
from config.config import CONFIG
from utils.logger import logger
from graphs.graph import create_graph


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="AI Agent Console Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s                          # Start with default configuration
  %(prog)s --working-dir /path      # Set working directory
  %(prog)s -w ~/projects            # Use short parameter to set working directory
  %(prog)s -r /path/to/debug        # Enable restricted mode for debugging in specific directory
  %(prog)s -r ~/project --allow-parent-read  # Restricted mode with parent directory read access
  
  LLM Configuration examples:
  %(prog)s --llm-model gpt-4         # Use GPT-4 model
  %(prog)s --llm-url https://api.openai.com/v1 --llm-api-key-env OPENAI_API_KEY  # Use OpenAI API
  %(prog)s --llm-model claude-3.5-sonnet --llm-url https://api.anthropic.com/v1  # Use Claude
  %(prog)s --llm-temperature 0.7 --llm-max-tokens 4096  # Fine-tune LLM parameters
        """,
    )

    parser.add_argument("--working-dir", "-w", type=str, help="Set the initial working directory for the Agent")

    parser.add_argument(
        "--restricted-dir", "-r", type=str, help="Enable restricted mode and confine AI to the specified directory"
    )

    parser.add_argument(
        "--allow-parent-read",
        action="store_true",
        help="In restricted mode, allow reading files from parent directories",
    )

    parser.add_argument(
        "--auto-mode",
        choices=["manual", "blacklist_reject", "universal_reject", "whitelist_accept", "universal_accept"],
        default="manual",
        help="Set automatic command handling mode (default: manual)",
    )

    # LLM configuration parameters
    parser.add_argument("--llm-model", type=str, help="Set LLM model name (e.g., deepseek-chat, gpt-4)")
    
    parser.add_argument("--llm-url", type=str, help="Set LLM API base URL (e.g., https://api.deepseek.com/v1)")
    
    parser.add_argument("--llm-api-key-env", type=str, help="Set environment variable name for LLM API key (e.g., DEEPSEEK_API_KEY)")
    
    parser.add_argument("--llm-max-tokens", type=int, help="Set maximum tokens for LLM response (default: 8192)")
    
    parser.add_argument("--llm-temperature", type=float, help="Set LLM temperature (0.0-2.0, default: 1.0)")

    parser.add_argument("--version", action="version", version="AI Agent Console v1.0.0")

    return parser.parse_args()


def main():
    """Main program"""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Set working directory
        if args.working_dir:
            # Expand user path (like ~)
            working_dir = os.path.expanduser(args.working_dir)

            # Check if directory exists
            if not os.path.exists(working_dir):
                print(f"❌ Working directory does not exist: {working_dir}")
                logger.error(f"Working directory does not exist: {working_dir}")
                return

            if not os.path.isdir(working_dir):
                print(f"❌ Specified path is not a directory: {working_dir}")
                logger.error(f"Specified path is not a directory: {working_dir}")
                return

            # Update configuration
            CONFIG["working_directory"] = os.path.abspath(working_dir)
            print(f"🗂️ Working directory set: {CONFIG['working_directory']}")
            logger.info(f"Working directory set: {CONFIG['working_directory']}")

        # Set restricted directory mode
        if args.restricted_dir:
            # Expand user path (like ~)
            restricted_dir = os.path.expanduser(args.restricted_dir)

            # Check if directory exists
            if not os.path.exists(restricted_dir):
                print(f"❌ Restricted directory does not exist: {restricted_dir}")
                logger.error(f"Restricted directory does not exist: {restricted_dir}")
                return

            if not os.path.isdir(restricted_dir):
                print(f"❌ Specified path is not a directory: {restricted_dir}")
                logger.error(f"Specified path is not a directory: {restricted_dir}")
                return

            # Enable restricted mode
            CONFIG["restricted_mode"] = True
            CONFIG["allowed_directory"] = os.path.abspath(restricted_dir)
            CONFIG["allow_parent_read"] = args.allow_parent_read

            # Also set as working directory if not already set
            if not args.working_dir:
                CONFIG["working_directory"] = CONFIG["allowed_directory"]

            # Display restriction info
            try:
                from utils.path_validator import format_restriction_info

                restriction_info = format_restriction_info()
                print(restriction_info)
                logger.info(f"Restricted mode enabled: {CONFIG['allowed_directory']}")
            except ImportError:
                print(f"🔒 Restricted mode enabled, directory: {CONFIG['allowed_directory']}")
                logger.info(f"Restricted mode enabled: {CONFIG['allowed_directory']}")

        # Set auto mode
        if args.auto_mode != "manual":
            CONFIG["auto_mode"] = args.auto_mode
            try:
                from tools.whitelist import get_auto_mode_description
                mode_description = get_auto_mode_description()
                print(mode_description)
                logger.info(f"Auto mode enabled: {args.auto_mode}")
            except ImportError:
                print(f"🤖 Auto mode enabled: {args.auto_mode}")
                logger.info(f"Auto mode enabled: {args.auto_mode}")

        # Set LLM configuration
        llm_config_changed = False
        if args.llm_model:
            CONFIG["llm_model_name"] = args.llm_model
            llm_config_changed = True
            print(f"🤖 LLM model set: {args.llm_model}")
            logger.info(f"LLM model set: {args.llm_model}")

        if args.llm_url:
            CONFIG["llm_base_url"] = args.llm_url
            llm_config_changed = True
            print(f"🌐 LLM API URL set: {args.llm_url}")
            logger.info(f"LLM API URL set: {args.llm_url}")

        if args.llm_api_key_env:
            CONFIG["llm_api_key_env"] = args.llm_api_key_env
            llm_config_changed = True
            print(f"🔑 LLM API key environment variable set: {args.llm_api_key_env}")
            logger.info(f"LLM API key environment variable set: {args.llm_api_key_env}")

        if args.llm_max_tokens:
            CONFIG["llm_max_tokens"] = args.llm_max_tokens
            llm_config_changed = True
            print(f"📏 LLM max tokens set: {args.llm_max_tokens}")
            logger.info(f"LLM max tokens set: {args.llm_max_tokens}")

        if args.llm_temperature is not None:
            CONFIG["llm_temperature"] = args.llm_temperature
            llm_config_changed = True
            print(f"🌡️ LLM temperature set: {args.llm_temperature}")
            logger.info(f"LLM temperature set: {args.llm_temperature}")

        if llm_config_changed:
            print("⚡ LLM configuration updated, will use new settings for agent initialization")

        # Display current configuration
        print(f"🤖 Using LLM model: {CONFIG['llm_model_name']}")
        print(f"🌐 LLM URL: {CONFIG['llm_base_url']}")
        print(f"🔑 LLM API key env: {CONFIG['llm_api_key_env']}")
        print()

        logger.info("Starting AI assistant system")

        # Initialize graph
        graph = create_graph()

        is_first = True
        messages_history = []

        while True:
            try:
                input_str = input("👤 You: ")

                input_state = {
                    "messages": (
                        preset_messages + [HumanMessage(content=input_str)]
                        if is_first
                        else [HumanMessage(content=input_str)]
                    ),
                }

                is_first = False

                print("⏳ Processing your request...", end="", flush=True)

                events = graph.stream(
                    input=input_state,
                    config={
                        "configurable": {"thread_id": CONFIG["thread_id"]},
                        "recursion_limit": CONFIG["recursion_limit"],
                    },
                    stream_mode=CONFIG["stream_mode"],
                )

                print("\r", end="", flush=True)  # Clear progress display

                for event in events:
                    if event.get("messages") and len(event["messages"]) > 0:
                        event["messages"][-1].pretty_print()
                        # Save messages to history
                        messages_history.extend(event["messages"])

            except KeyboardInterrupt:
                print("\n\n👋 Exiting program")
                break
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                print(f"🚫 Error occurred, please try again: {e}")

    except Exception as e:
        logger.error(f"System startup failed: {e}")
        print(f"🚫 System startup failed: {e}")


if __name__ == "__main__":
    main()
