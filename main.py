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
