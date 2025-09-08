#!/usr/bin/env python3
"""
Web服务器 - 为前端提供API接口与agent交互
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import json
import os
import queue
import argparse

# 导入现有的agent系统
from main import create_graph
from states.state import State
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config.config import CONFIG
from utils.logger import logger
from utils.singleton_dict import get_monitored_dict, add_dict_observer, get_dict_history

# from utils.preset import preset_messages

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量来存储agent图和待确认的命令
agent_graph = None

# 使用单例字典管理器创建被监控的字典
pending_confirmations = get_monitored_dict(
    "pending_confirmations"
)  # 存储待确认的命令: {session_id: {command: str, callback: callable}}
sse_clients = get_monitored_dict("sse_clients")  # 存储SSE客户端连接: {session_id: [client_generators, ...]}


def initialize_agent(web_mode=True):
    """初始化agent图"""
    global agent_graph
    try:
        agent_graph = create_graph(web_mode=web_mode)

        # 设置字典观察者
        setup_dict_observers()

        logger.info(f"Agent系统初始化成功 (Web模式: {'启用' if web_mode else '禁用'})")
        return True
    except Exception as e:
        logger.error(f"Agent系统初始化失败: {e}")
        return False


def setup_dict_observers():
    """设置字典修改观察者"""

    def on_pending_confirmations_change(dict_name, operation, key, value, old_value):
        """pending_confirmations 字典修改时的回调"""
        if operation == "set" and old_value is None:
            logger.info(f"新增待确认命令: session_id={key}, command={value.get('command', 'unknown')}")
        elif operation == "delete":
            logger.info(f"移除待确认命令: session_id={key}")

    def on_sse_clients_change(dict_name, operation, key, value, old_value):
        """sse_clients 字典修改时的回调"""
        if operation == "set":
            if old_value is None:
                logger.info(f"新增SSE客户端连接: session_id={key}, 客户端数量={len(value) if value else 0}")
            else:
                logger.info(f"更新SSE客户端连接: session_id={key}, 客户端数量={len(value) if value else 0}")
        elif operation == "delete":
            logger.info(f"移除SSE客户端连接: session_id={key}")

    # 添加观察者
    add_dict_observer("pending_confirmations", on_pending_confirmations_change)
    add_dict_observer("sse_clients", on_sse_clients_change)


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok", "agent_ready": agent_graph is not None, "message": "AI Agent Web服务正常运行"})


@app.route("/api/dict-history", methods=["GET"])
def get_dict_modification_history():
    """获取字典修改历史"""
    try:
        dict_name = request.args.get("dict_name")  # 可选参数，指定字典名称
        limit = int(request.args.get("limit", 50))  # 限制返回数量，默认50

        history = get_dict_history(dict_name, limit)

        # 格式化时间戳为可读格式
        import datetime

        for record in history:
            record["readable_time"] = datetime.datetime.fromtimestamp(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(
            {"status": "success", "history": history, "total_records": len(history), "dict_name": dict_name or "all"}
        )

    except Exception as e:
        logger.error(f"获取字典修改历史时出错: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/dict-status", methods=["GET"])
def get_dict_status():
    """获取所有字典的状态信息"""
    try:
        from utils.singleton_dict import dict_manager

        all_dicts = dict_manager.get_all_dict_names()
        dict_status = {}

        for dict_name in all_dicts:
            info = dict_manager.get_dict_info(dict_name)
            dict_status[dict_name] = info

        return jsonify({"status": "success", "dictionaries": dict_status, "total_dicts": len(all_dicts)})

    except Exception as e:
        logger.error(f"获取字典状态时出错: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/pending-confirmations", methods=["GET"])
def get_pending_confirmations():
    """获取待确认的命令列表"""
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
    """确认或拒绝命令执行"""
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")
        confirmed = data.get("confirmed", False)

        if session_id not in pending_confirmations:
            return jsonify({"status": "error", "message": "没有找到待确认的命令"}), 404

        # 获取回调函数
        callback = pending_confirmations[session_id]["callback"]
        command = pending_confirmations[session_id]["command"]

        # 清除待确认状态
        del pending_confirmations[session_id]

        # 执行回调
        if callback:
            callback(confirmed)

        logger.info(f"用户{'确认' if confirmed else '拒绝'}执行命令: {command}")

        return jsonify(
            {"status": "success", "message": f"命令已{'确认' if confirmed else '拒绝'}", "confirmed": confirmed}
        )

    except Exception as e:
        logger.error(f"处理命令确认时出错: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/events", methods=["GET"])
def events():
    """Server-Sent Events接口，用于推送确认请求"""
    session_id = request.args.get("session_id", "default")

    def event_stream():
        # 发送连接成功消息
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

        # 创建一个队列来接收事件
        event_queue = queue.Queue()
        # 将此客户端添加到全局客户端列表
        if session_id not in sse_clients:
            sse_clients[session_id] = []
        sse_clients[session_id].append(event_queue)
        print(f"SSE客户端已注册: {session_id}, 当前客户端数: {len(sse_clients[session_id])}")
        print(f"所有会话: {list(sse_clients.keys())}")
        print(f"SSE客户端: {sse_clients}")

        try:
            while True:
                try:
                    # 等待事件，设置超时以便定期发送心跳
                    event = event_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # 发送心跳保持连接
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                except GeneratorExit:
                    break
        finally:
            # 清理客户端连接
            if session_id in sse_clients and event_queue in sse_clients[session_id]:
                sse_clients[session_id].remove(event_queue)
                if not sse_clients[session_id]:
                    print(f"SSE客户端已清理: {session_id}")
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
    """向指定会话的所有SSE客户端发送事件"""
    print(f"准备发送SSE事件: {event_data}")
    print(f"SSE客户端: {sse_clients}")
    print(f"会话ID: {session_id}")

    if session_id in sse_clients:
        dead_clients = []
        for client_queue in sse_clients[session_id]:
            try:
                print(f"发送SSE事件: {event_data}")
                client_queue.put(event_data, timeout=1)
            except queue.Full:
                # 客户端队列满，可能已断开连接
                dead_clients.append(client_queue)
            except Exception as e:
                logger.warning(f"发送SSE事件失败: {e}")
                dead_clients.append(client_queue)

        # 清理已断开的客户端
        for dead_client in dead_clients:
            if dead_client in sse_clients[session_id]:
                sse_clients[session_id].remove(dead_client)


def process_message(messages: list, session_id: str = "default") -> str:
    """处理完整对话历史并返回agent响应"""
    try:
        # 将OpenAI格式的消息转换为LangChain格式
        langchain_messages = []

        # 添加preset_messages作为系统上下文
        # langchain_messages.extend(preset_messages)

        # 转换对话历史
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))

        # 构建输入状态
        input_state = {
            "messages": langchain_messages,
            "session_id": session_id,
        }

        # 调用agent处理（无状态）
        events = agent_graph.stream(
            input=input_state,
            config={
                "recursion_limit": CONFIG["recursion_limit"],
            },
            stream_mode=CONFIG["stream_mode"],
        )

        # 收集响应
        response_messages = []
        for event in events:
            if event.get("messages") and len(event["messages"]) > 0:
                response_messages.extend(event["messages"])

        # 提取最后的AI响应
        if response_messages:
            last_message = response_messages[-1]
            if isinstance(last_message, AIMessage):
                return last_message.content
            else:
                return str(last_message.content)
        else:
            return "抱歉，我无法处理您的请求。"

    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        raise e


def get_timestamp():
    """获取当前时间戳"""
    from datetime import datetime

    return datetime.now().isoformat()


# ==================== OpenAI兼容API ====================


@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    """OpenAI兼容的聊天完成接口，用于SillyTavern集成"""
    try:
        data = request.get_json()

        # 获取请求参数
        messages = data.get("messages", [])
        model = data.get("model", "my-agent")
        stream = data.get("stream", False)
        max_tokens = data.get("max_tokens", 2000)
        temperature = data.get("temperature", 0.7)

        if not messages:
            return jsonify({"error": {"message": "messages cannot be empty", "type": "invalid_request_error"}}), 400

        if not agent_graph:
            return jsonify({"error": {"message": "Agent system not initialized", "type": "internal_server_error"}}), 500

        # 提取最后一条用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message:
            return jsonify({"error": {"message": "No user message found", "type": "invalid_request_error"}}), 400

        logger.info(f"OpenAI API请求 - 模型: {model}, 用户消息: {user_message[:100]}...")

        # 从请求头或参数中获取session_id
        session_id = request.headers.get("X-Session-ID", "default")
        print(f"收到聊天请求 - 会话ID: {session_id}")
        print(f"请求头: {dict(request.headers)}")

        if stream:
            # 流式响应
            return handle_streaming_response(model, messages, session_id)
        else:
            # 非流式响应
            return handle_non_streaming_response(model, messages, session_id)

    except Exception as e:
        logger.error(f"处理OpenAI API请求时出错: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


def handle_non_streaming_response(model: str, original_messages: list, session_id: str = "default"):
    """处理非流式响应"""
    try:
        # 处理消息
        response_content = process_message(original_messages, session_id)

        # 构建OpenAI兼容的响应格式
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
        logger.error(f"处理非流式响应时出错: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


def handle_streaming_response(model: str, messages: list, session_id: str = "default"):
    """处理流式响应"""
    try:
        from flask import Response
        import uuid
        import json

        def generate():
            try:
                # 将OpenAI格式的消息转换为LangChain格式
                langchain_messages = []

                # 添加preset_messages作为系统上下文
                # langchain_messages.extend(preset_messages)

                # 转换对话历史
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")

                    if role == "user":
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        langchain_messages.append(AIMessage(content=content))
                    elif role == "system":
                        langchain_messages.append(SystemMessage(content=content))

                # 构建输入状态
                input_state = {
                    "messages": langchain_messages,
                    "session_id": session_id,
                }

                completion_id = str(uuid.uuid4())[:8]

                # 发送开始事件
                start_chunk = {
                    "id": f"chatcmpl-{completion_id}",
                    "object": "chat.completion.chunk",
                    "created": int(get_timestamp_unix()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(start_chunk)}\n\n"

                # 流式处理agent响应
                accumulated_content = ""

                events = agent_graph.stream(
                    input=input_state,
                    config={
                        "recursion_limit": CONFIG["recursion_limit"],
                    },
                    stream_mode="messages",  # 使用messages模式获得更细粒度的流式输出
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

                # 发送结束事件
                end_chunk = {
                    "id": f"chatcmpl-{completion_id}",
                    "object": "chat.completion.chunk",
                    "created": int(get_timestamp_unix()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(end_chunk)}\n\n"

                # 发送结束标记
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"流式响应生成过程中出错: {e}")
                # 发送错误信息
                error_chunk = {
                    "id": f"chatcmpl-error",
                    "object": "chat.completion.chunk",
                    "created": int(get_timestamp_unix()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"抱歉，处理您的请求时出现错误: {str(e)}"},
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
        logger.error(f"处理流式响应时出错: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


@app.route("/v1/models", methods=["GET"])
def list_models():
    """列出可用的模型（OpenAI兼容接口）"""
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
    """简单的token数量估算（大约1token=4字符）"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_timestamp_unix():
    """获取Unix时间戳"""
    from datetime import datetime

    return int(datetime.now().timestamp())


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AI Agent Web服务器 - 提供OpenAI兼容的API接口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s                          # 使用默认配置启动
  %(prog)s --port 8080              # 在8080端口启动
  %(prog)s --host 127.0.0.1         # 仅允许本地访问
  %(prog)s --debug                  # 启用调试模式
  %(prog)s --no-web-mode            # 禁用Web模式
  %(prog)s --port 8080 --debug      # 在8080端口启动并启用调试模式
        """
    )
    
    # 服务器配置参数
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="服务器监听的主机地址 (默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=5000,
        help="服务器监听的端口号 (默认: 5000)"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="启用Flask调试模式 (默认: 关闭)"
    )
    
    parser.add_argument(
        "--no-debug", 
        action="store_true",
        help="强制禁用调试模式"
    )
    
    # Agent配置参数
    parser.add_argument(
        "--web-mode", 
        action="store_true", 
        default=True,
        help="启用Web模式 (默认: 启用)"
    )
    
    parser.add_argument(
        "--no-web-mode", 
        action="store_true",
        help="禁用Web模式"
    )
    
    # 日志配置参数
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="设置日志级别 (默认: INFO)"
    )
    
    # 其他选项
    parser.add_argument(
        "--version", 
        action="version", 
        version="AI Agent Web Server v1.0.0"
    )
    
    args = parser.parse_args()
    
    # 处理互斥选项
    if args.no_debug:
        args.debug = False
    
    if args.no_web_mode:
        args.web_mode = False
    
    return args


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    logger.setLevel(getattr(logging, args.log_level))
    
    # 打印启动信息
    print("🚀 启动AI Agent API服务器 (SillyTavern兼容)...")
    print(f"📡 服务器地址: {args.host}:{args.port}")
    print(f"🌐 OpenAI API: http://{args.host}:{args.port}/v1/chat/completions")
    print(f"📊 健康检查: http://{args.host}:{args.port}/api/health")
    print(f"🔧 调试模式: {'启用' if args.debug else '禁用'}")
    print(f"🌍 Web模式: {'启用' if args.web_mode else '禁用'}")
    print(f"📝 日志级别: {args.log_level}")
    print()
    
    # 初始化agent系统
    if initialize_agent(web_mode=args.web_mode):
        logger.info(f"正在启动Web服务器 {args.host}:{args.port}")
        
        try:
            # 启动服务器
            app.run(
                host=args.host, 
                port=args.port, 
                debug=args.debug,
                use_reloader=False  # 避免在调试模式下重复初始化
            )
        except KeyboardInterrupt:
            print("\n👋 服务器已停止")
            logger.info("服务器收到停止信号")
        except Exception as e:
            print(f"❌ 服务器启动失败: {e}")
            logger.error(f"服务器启动失败: {e}")
    else:
        print("❌ Agent系统初始化失败，无法启动Web服务器")
        exit(1)
