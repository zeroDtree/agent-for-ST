#!/usr/bin/env python3
"""
Web Server - Provides API interface for frontend to interact with agent
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import json
import os
import queue
import argparse

# Import existing agent system
from graphs.graph import create_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config.config import CONFIG
from utils.logger import logger
from utils.singleton_dict import get_monitored_dict, add_dict_observer, get_dict_history

# from utils.preset import preset_messages

app = Flask(__name__)
CORS(app)  # allow cross-origin requests

# Global variables to store agent graph and pending commands
agent_graph = None

# Use singleton dictionary manager to create monitored dictionaries
pending_confirmations = get_monitored_dict(
    "pending_confirmations"
)  # Store pending commands: {session_id: {command: str, callback: callable}}
sse_clients = get_monitored_dict("sse_clients")  # Store SSE client connections: {session_id: [client_generators, ...]}


def initialize_agent(web_mode=True):
    """Initialize agent graph"""
    global agent_graph
    try:
        agent_graph = create_graph(web_mode=web_mode)

        # Set up dictionary observers
        setup_dict_observers()

        logger.info(f"Agent system initialized successfully (Web mode: {'Enabled' if web_mode else 'Disabled'})")
        return True
    except Exception as e:
        logger.error(f"Agent system initialization failed: {e}")
        return False


def setup_dict_observers():
    """Set up dictionary modification observers"""

    def on_pending_confirmations_change(dict_name, operation, key, value, old_value):
        """Callback for pending_confirmations dictionary modifications"""
        if operation == "set" and old_value is None:
            logger.info(f"New pending command added: session_id={key}, command={value.get('command', 'unknown')}")
        elif operation == "delete":
            logger.info(f"Pending command removed: session_id={key}")

    def on_sse_clients_change(dict_name, operation, key, value, old_value):
        """Callback for sse_clients dictionary modifications"""
        if operation == "set":
            if old_value is None:
                logger.info(
                    f"New SSE client connection added: session_id={key}, client_count={len(value) if value else 0}"
                )
            else:
                logger.info(
                    f"SSE client connection updated: session_id={key}, client_count={len(value) if value else 0}"
                )
        elif operation == "delete":
            logger.info(f"SSE client connection removed: session_id={key}")

    # Add observers
    add_dict_observer("pending_confirmations", on_pending_confirmations_change)
    add_dict_observer("sse_clients", on_sse_clients_change)


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {"status": "ok", "agent_ready": agent_graph is not None, "message": "AI Agent Web service is running normally"}
    )


@app.route("/api/dict-history", methods=["GET"])
def get_dict_modification_history():
    """Get dictionary modification history"""
    try:
        dict_name = request.args.get("dict_name")  # Optional parameter to specify dictionary name
        limit = int(request.args.get("limit", 50))  # Limit return count, default 50

        history = get_dict_history(dict_name, limit)

        # Format timestamp to readable format
        import datetime

        for record in history:
            record["readable_time"] = datetime.datetime.fromtimestamp(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(
            {"status": "success", "history": history, "total_records": len(history), "dict_name": dict_name or "all"}
        )

    except Exception as e:
        logger.error(f"Error getting dictionary modification history: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/dict-status", methods=["GET"])
def get_dict_status():
    """Get status information for all dictionaries"""
    try:
        from utils.singleton_dict import dict_manager

        all_dicts = dict_manager.get_all_dict_names()
        dict_status = {}

        for dict_name in all_dicts:
            info = dict_manager.get_dict_info(dict_name)
            dict_status[dict_name] = info

        return jsonify({"status": "success", "dictionaries": dict_status, "total_dicts": len(all_dicts)})

    except Exception as e:
        logger.error(f"Error getting dictionary status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/restriction-status", methods=["GET"])
def get_restriction_status():
    """Get current directory restriction status"""
    try:
        restriction_info = {
            "restricted_mode": CONFIG.get("restricted_mode", False),
            "allowed_directory": CONFIG.get("allowed_directory"),
            "allow_parent_read": CONFIG.get("allow_parent_read", False),
            "enforce_strict_sandbox": CONFIG.get("enforce_strict_sandbox", True),
            "working_directory": CONFIG.get("working_directory"),
            "auto_mode": CONFIG.get("auto_mode", "manual"),
        }

        # Add formatted info if available
        try:
            from utils.path_validator import format_restriction_info

            restriction_info["formatted_info"] = format_restriction_info()
        except ImportError:
            restriction_info["formatted_info"] = "Path validator not available"

        return jsonify(
            {
                "status": "success",
                "restriction": restriction_info,
                "message": "🔒 Restricted mode" if restriction_info["restricted_mode"] else "🔓 Normal mode",
            }
        )

    except Exception as e:
        logger.error(f"Error getting restriction status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/pending-confirmations", methods=["GET"])
def get_pending_confirmations():
    """Get list of pending commands for confirmation"""
    session_id = request.args.get("session_id", "default")
    if session_id in pending_confirmations:
        return jsonify(
            {
                "status": "success",
                "pending": True,
                "command": pending_confirmations[session_id]["command"],
                "tool_name": pending_confirmations[session_id].get("tool_name", "unknown"),
                "session_id": session_id,
            }
        )
    else:
        return jsonify({"status": "success", "pending": False, "session_id": session_id})


@app.route("/api/confirm-command", methods=["POST"])
def confirm_command():
    """Confirm or reject command execution"""
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")
        confirmed = data.get("confirmed", False)

        if session_id not in pending_confirmations:
            return jsonify({"status": "error", "message": "No pending command found"}), 404

        # Get callback function
        callback = pending_confirmations[session_id]["callback"]
        command = pending_confirmations[session_id]["command"]

        # Clear pending status
        del pending_confirmations[session_id]

        # Execute callback
        if callback:
            callback(confirmed)

        logger.info(f"User {'confirmed' if confirmed else 'rejected'} command execution: {command}")

        return jsonify(
            {
                "status": "success",
                "message": f"Command {'confirmed' if confirmed else 'rejected'}",
                "confirmed": confirmed,
            }
        )

    except Exception as e:
        logger.error(f"Error processing command confirmation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/events", methods=["GET"])
def events():
    """Server-Sent Events interface for pushing confirmation requests"""
    session_id = request.args.get("session_id", "default")

    def event_stream():
        # Send connection success message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

        # Create a queue to receive events
        event_queue = queue.Queue()
        # Add this client to global client list
        if session_id not in sse_clients:
            sse_clients[session_id] = []
        sse_clients[session_id].append(event_queue)
        print(f"SSE client registered: {session_id}, current client count: {len(sse_clients[session_id])}")
        print(f"All sessions: {list(sse_clients.keys())}")
        print(f"SSE clients: {sse_clients}")

        try:
            while True:
                try:
                    # Wait for events, set timeout for periodic heartbeat
                    event = event_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                except GeneratorExit:
                    break
        finally:
            # Clean up client connections
            if session_id in sse_clients and event_queue in sse_clients[session_id]:
                sse_clients[session_id].remove(event_queue)
                if not sse_clients[session_id]:
                    print(f"SSE client cleaned up: {session_id}")
                    del sse_clients[session_id]

    return app.response_class(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


def send_sse_event(session_id: str, event_data: dict):
    """Send events to all SSE clients of specified session"""
    print(f"Preparing to send SSE event: {event_data}")
    print(f"SSE clients: {sse_clients}")
    print(f"Session ID: {session_id}")

    if session_id in sse_clients:
        dead_clients = []
        for client_queue in sse_clients[session_id]:
            try:
                print(f"Sending SSE event: {event_data}")
                client_queue.put(event_data, timeout=1)
            except queue.Full:
                # Client queue full, possibly disconnected
                dead_clients.append(client_queue)
            except Exception as e:
                logger.warning(f"Failed to send SSE event: {e}")
                dead_clients.append(client_queue)

        # Clean up disconnected clients
        for dead_client in dead_clients:
            if dead_client in sse_clients[session_id]:
                sse_clients[session_id].remove(dead_client)


def process_message(messages: list, session_id: str = "default") -> str:
    """Process complete conversation history and return agent response"""
    try:
        # Convert OpenAI format messages to LangChain format
        langchain_messages = []

        # Add preset_messages as system context
        # langchain_messages.extend(preset_messages)

        # Convert conversation history
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))

        # Build input state
        input_state = {
            "messages": langchain_messages,
            "session_id": session_id,
        }

        # Call agent processing (stateless)
        events = agent_graph.stream(
            input=input_state,
            config={
                "recursion_limit": CONFIG["recursion_limit"],
            },
            stream_mode=CONFIG["stream_mode"],
        )

        # Collect responses
        response_messages = []
        for event in events:
            if event.get("messages") and len(event["messages"]) > 0:
                response_messages.extend(event["messages"])

        # Extract last AI response
        if response_messages:
            last_message = response_messages[-1]
            if isinstance(last_message, AIMessage):
                return last_message.content
            else:
                return str(last_message.content)
        else:
            return "Sorry, I cannot process your request."

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise e


def get_timestamp():
    """Get current timestamp"""
    from datetime import datetime

    return datetime.now().isoformat()


# ==================== OpenAI Compatible API ====================


@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    """OpenAI compatible chat completion interface for SillyTavern integration"""
    try:
        data = request.get_json()

        # Get request parameters
        messages = data.get("messages", [])
        model = data.get("model", "my-agent")
        stream = data.get("stream", False)
        max_tokens = data.get("max_tokens", 2000)
        temperature = data.get("temperature", 0.7)

        if not messages:
            return jsonify({"error": {"message": "messages cannot be empty", "type": "invalid_request_error"}}), 400

        if not agent_graph:
            return jsonify({"error": {"message": "Agent system not initialized", "type": "internal_server_error"}}), 500

        # Extract last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message:
            return jsonify({"error": {"message": "No user message found", "type": "invalid_request_error"}}), 400

        logger.info(f"OpenAI API request - Model: {model}, User message: {user_message[:100]}...")

        # Get session_id from request headers or parameters
        session_id = request.headers.get("X-Session-ID", "default")
        print(f"Received chat request - Session ID: {session_id}")
        print(f"Request headers: {dict(request.headers)}")

        if stream:
            # Streaming response
            return handle_streaming_response(model, messages, session_id)
        else:
            # Non-streaming response
            return handle_non_streaming_response(model, messages, session_id)

    except Exception as e:
        logger.error(f"Error processing OpenAI API request: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


def handle_non_streaming_response(model: str, original_messages: list, session_id: str = "default"):
    """Handle non-streaming response"""
    try:
        # Process messages
        response_content = process_message(original_messages, session_id)

        # Build OpenAI compatible response format
        import uuid

        completion_id = str(uuid.uuid4())[:8]
        response = {
            "id": f"chatcmpl-{completion_id}",
            "object": "chat.completion",
            "created": int(get_timestamp_unix()),
            "model": model,
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": response_content}, "finish_reason": "stop"}
            ],
            "usage": {
                "prompt_tokens": estimate_tokens(str(original_messages)),
                "completion_tokens": estimate_tokens(response_content),
                "total_tokens": estimate_tokens(str(original_messages)) + estimate_tokens(response_content),
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error handling non-streaming response: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


def handle_streaming_response(model: str, messages: list, session_id: str = "default"):
    """Handle streaming response"""
    try:
        from flask import Response
        import uuid
        import json

        def generate():
            try:
                # Convert OpenAI format messages to LangChain format
                langchain_messages = []

                # Add preset_messages as system context
                # langchain_messages.extend(preset_messages)

                # Convert conversation history
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")

                    if role == "user":
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        langchain_messages.append(AIMessage(content=content))
                    elif role == "system":
                        langchain_messages.append(SystemMessage(content=content))

                # Build input state
                input_state = {
                    "messages": langchain_messages,
                    "session_id": session_id,
                }

                completion_id = str(uuid.uuid4())[:8]

                # Send start event
                start_chunk = {
                    "id": f"chatcmpl-{completion_id}",
                    "object": "chat.completion.chunk",
                    "created": int(get_timestamp_unix()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(start_chunk)}\n\n"

                # Stream process agent response
                accumulated_content = ""

                events = agent_graph.stream(
                    input=input_state,
                    config={
                        "recursion_limit": CONFIG["recursion_limit"],
                    },
                    stream_mode="messages",  # Use messages mode for finer-grained streaming output
                )

                for message_chunk, metadata in events:
                    if message_chunk.content and metadata["langgraph_node"] not in ["my_tools"]:
                        accumulated_content = message_chunk.content

                        chunk = {
                            "id": f"chatcmpl-{completion_id}",
                            "object": "chat.completion.chunk",
                            "created": int(get_timestamp_unix()),
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": accumulated_content}, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                # Send end event
                end_chunk = {
                    "id": f"chatcmpl-{completion_id}",
                    "object": "chat.completion.chunk",
                    "created": int(get_timestamp_unix()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(end_chunk)}\n\n"

                # Send end marker
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error during streaming response generation: {e}")
                # Send error information
                error_chunk = {
                    "id": f"chatcmpl-error",
                    "object": "chat.completion.chunk",
                    "created": int(get_timestamp_unix()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"Sorry, an error occurred while processing your request: {str(e)}"},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return Response(
            generate(),
            mimetype="text/plain",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    except Exception as e:
        logger.error(f"Error handling streaming response: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


@app.route("/v1/models", methods=["GET"])
def list_models():
    """List available models (OpenAI compatible interface)"""
    return jsonify(
        {
            "object": "list",
            "data": [
                {
                    "id": "my-agent",
                    "object": "model",
                    "created": int(get_timestamp_unix()),
                    "owned_by": "my-agent-system",
                    "permission": [],
                    "root": "my-agent",
                    "parent": None,
                }
            ],
        }
    )


def estimate_tokens(text: str) -> int:
    """Simple token count estimation (approximately 1 token = 4 characters)"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_timestamp_unix():
    """Get Unix timestamp"""
    from datetime import datetime

    return int(datetime.now().timestamp())


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="AI Agent Web Server - Provides OpenAI compatible API interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s                          # Start with default configuration
  %(prog)s --port 8080              # Start on port 8080
  %(prog)s --host 127.0.0.1         # Allow local access only
  %(prog)s --debug                  # Enable debug mode
  %(prog)s --no-web-mode            # Disable web mode
  %(prog)s --working-dir ~/projects # Set working directory
  %(prog)s -w /path/to/work         # Use short parameter to set working directory
  %(prog)s -r /path/to/debug        # Enable restricted mode for debugging
  %(prog)s -r ~/project --allow-parent-read  # Restricted mode with parent directory access
  %(prog)s --port 8080 --debug -r ~/debug    # Combined: custom port, debug mode, and restriction
        """,
    )

    # Server configuration parameters
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server listening host address (default: 0.0.0.0)")

    parser.add_argument("--port", type=int, default=5000, help="Server listening port number (default: 5000)")

    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode (default: off)")

    parser.add_argument("--no-debug", action="store_true", help="Force disable debug mode")

    # Agent configuration parameters
    parser.add_argument("--web-mode", action="store_true", default=True, help="Enable Web mode (default: enabled)")

    parser.add_argument("--no-web-mode", action="store_true", help="Disable Web mode")

    # Log configuration parameters
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set log level (default: INFO)",
    )

    # Working directory parameters
    parser.add_argument("--working-dir", "-w", type=str, help="Set the initial working directory for the Agent")

    # Directory restriction parameters
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

    # Other options
    parser.add_argument("--version", action="version", version="AI Agent Web Server v1.0.0")

    args = parser.parse_args()

    # Handle mutually exclusive options
    if args.no_debug:
        args.debug = False

    if args.no_web_mode:
        args.web_mode = False

    return args


if __name__ == "__main__":
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
            exit(1)

        if not os.path.isdir(working_dir):
            print(f"❌ Specified path is not a directory: {working_dir}")
            logger.error(f"Specified path is not a directory: {working_dir}")
            exit(1)

        # Update configuration
        CONFIG["working_directory"] = os.path.abspath(working_dir)
        print(f"🗂️ Working directory set: {CONFIG['working_directory']}")

    # Set restricted directory mode
    if args.restricted_dir:
        # Expand user path (like ~)
        restricted_dir = os.path.expanduser(args.restricted_dir)

        # Check if directory exists
        if not os.path.exists(restricted_dir):
            print(f"❌ Restricted directory does not exist: {restricted_dir}")
            logger.error(f"Restricted directory does not exist: {restricted_dir}")
            exit(1)

        if not os.path.isdir(restricted_dir):
            print(f"❌ Specified path is not a directory: {restricted_dir}")
            logger.error(f"Specified path is not a directory: {restricted_dir}")
            exit(1)

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
            logger.info(f"Web server restricted mode enabled: {CONFIG['allowed_directory']}")
        except ImportError:
            print(f"🔒 Restricted mode enabled, directory: {CONFIG['allowed_directory']}")
            logger.info(f"Web server restricted mode enabled: {CONFIG['allowed_directory']}")

    # Set auto mode
    if args.auto_mode != "manual":
        CONFIG["auto_mode"] = args.auto_mode
        try:
            from tools.whitelist import get_auto_mode_description

            mode_description = get_auto_mode_description()
            print(mode_description)
            logger.info(f"Web server auto mode enabled: {args.auto_mode}")
        except ImportError:
            print(f"🤖 Auto mode enabled: {args.auto_mode}")
            logger.info(f"Web server auto mode enabled: {args.auto_mode}")

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    logger.setLevel(getattr(logging, args.log_level))

    # Print startup information
    print("🚀 Starting AI Agent API Server (SillyTavern compatible)...")
    print(f"📡 Server address: {args.host}:{args.port}")
    print(f"🌐 OpenAI API: http://{args.host}:{args.port}/v1/chat/completions")
    print(f"📊 Health check: http://{args.host}:{args.port}/api/health")
    print(f"🔧 Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    print(f"🌍 Web mode: {'Enabled' if args.web_mode else 'Disabled'}")
    if args.working_dir:
        print(f"🗂️ Working directory: {CONFIG['working_directory']}")
    print(f"📝 Log level: {args.log_level}")
    print()

    # Initialize agent system
    if initialize_agent(web_mode=args.web_mode):
        logger.info(f"Starting web server {args.host}:{args.port}")

        try:
            # Start server
            app.run(
                host=args.host,
                port=args.port,
                debug=args.debug,
                use_reloader=False,  # Avoid duplicate initialization in debug mode
            )
        except KeyboardInterrupt:
            print("\n👋 Server stopped")
            logger.info("Server received stop signal")
        except Exception as e:
            print(f"❌ Server startup failed: {e}")
            logger.error(f"Server startup failed: {e}")
    else:
        print("❌ Agent system initialization failed, unable to start web server")
        exit(1)
