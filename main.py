from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

# 配置和utils
from config.config import CONFIG
from utils.logger import logger
from utils.monitor import monitor_performance
from utils.history import cleanup_old_messages
from utils.cache import cached_is_safe_command

# 自定义包
from llms.llm_with_tools import llm_with_tools
from tools import ALL_TOOLS
from states.state import State
from nodes.human import get_human_confirm_node
from utils.preset import preset_messages

# langchain.debug = True


@monitor_performance
def chatbot(state: State):
    """主聊天函数，带性能监控"""
    state["messages"] = cleanup_old_messages(state["messages"])
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def create_graph(tools=None, checkpointer=None):
    """创建图结构，支持依赖注入"""
    if tools is None:
        tools = ALL_TOOLS

    if checkpointer is None:
        checkpointer = InMemorySaver()

    tool_node = ToolNode(tools=tools)
    graph_builder = StateGraph(State)

    graph_builder.add_node("my_tools", tool_node)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node(
        "human_confirm", get_human_confirm_node(next_node_for_yes="my_tools", next_node_for_no="chatbot")
    )
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("my_tools", "chatbot")

    def chatbot_route(state: State):
        """路由函数，处理工具调用"""
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")

        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            # 检查是否是shell命令工具调用
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name in ["run_shell_command_tool", "run_shell_command_popen_tool"]:
                    # 提取命令参数
                    args = tool_call.get("args", {})
                    command = args.get("command", "")

                    # 使用缓存的白名单检查
                    if cached_is_safe_command(command):
                        print(f"🟢 白名单命令，直接执行: {command}")
                        return "my_tools"

            # 非白名单命令或非shell命令，需要用户确认
            print(f"⚠️ 非白名单命令，需要确认: {command}")
            return "human_confirm"
        return END

    graph_builder.add_conditional_edges(
        "chatbot",
        chatbot_route,
    )

    return graph_builder.compile(checkpointer=checkpointer)


def main():
    """主程序"""
    try:
        logger.info("启动AI助手系统")

        # 初始化图
        graph = create_graph()

        is_first = True
        messages_history = []

        while True:
            try:
                input_str = input("👤 您: ")

                input_state = {
                    "messages": (
                        preset_messages + [HumanMessage(content=input_str)]
                        if is_first
                        else [HumanMessage(content=input_str)]
                    ),
                }

                is_first = False

                print("⏳ 正在处理您的请求...", end="", flush=True)

                events = graph.stream(
                    input=input_state,
                    config={
                        "configurable": {"thread_id": CONFIG["thread_id"]},
                        "recursion_limit": CONFIG["recursion_limit"],
                    },
                    stream_mode=CONFIG["stream_mode"],
                )

                print("\r", end="", flush=True)  # 清除进度显示

                for event in events:
                    if event.get("messages") and len(event["messages"]) > 0:
                        event["messages"][-1].pretty_print()
                        # 保存消息到历史
                        messages_history.extend(event["messages"])

            except KeyboardInterrupt:
                print("\n\n👋 退出程序")
                break
            except Exception as e:
                logger.error(f"处理请求时出错: {e}")
                print(f"🚫 出现错误，请重试: {e}")

    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        print(f"🚫 系统启动失败: {e}")


if __name__ == "__main__":
    main()
