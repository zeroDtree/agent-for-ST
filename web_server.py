#!/usr/bin/env python3
"""
Web服务器 - 为前端提供API接口与agent交互
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import json
import os

# 导入现有的agent系统
from main import create_graph
from states.state import State
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config.config import CONFIG
from utils.logger import logger
# from utils.preset import preset_messages

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量来存储agent图
agent_graph = None


def initialize_agent():
    """初始化agent图"""
    global agent_graph
    try:
        agent_graph = create_graph()
        logger.info("Agent系统初始化成功")
        return True
    except Exception as e:
        logger.error(f"Agent系统初始化失败: {e}")
        return False


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok", "agent_ready": agent_graph is not None, "message": "AI Agent Web服务正常运行"})


def process_message(messages: list) -> str:
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

        if stream:
            # 流式响应
            return handle_streaming_response(model, messages)
        else:
            # 非流式响应
            return handle_non_streaming_response(model, messages)

    except Exception as e:
        logger.error(f"处理OpenAI API请求时出错: {e}")
        return jsonify({"error": {"message": str(e), "type": "internal_server_error"}}), 500


def handle_non_streaming_response(model: str, original_messages: list):
    """处理非流式响应"""
    try:
        # 处理消息
        response_content = process_message(original_messages)

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


def handle_streaming_response(model: str, messages: list):
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


if __name__ == "__main__":
    # 初始化agent系统
    if initialize_agent():
        print("🚀 启动AI Agent API服务器 (SillyTavern兼容)...")
        print("🌐 OpenAI API: http://localhost:5000/v1/chat/completions")
        print("📊 健康检查: http://localhost:5000/api/health")

        # 启动服务器
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        print("❌ Agent系统初始化失败，无法启动Web服务器")
