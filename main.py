from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

# 配置和utils
from config.config import CONFIG, TOOL_SECURITY_CONFIG
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


def create_graph(tools=None, checkpointer=None, web_mode=False):
    """创建图结构，支持依赖注入"""
    if tools is None:
        tools = ALL_TOOLS

    # if checkpointer is None:
    #     checkpointer = InMemorySaver()

    tool_node = ToolNode(tools=tools)
    graph_builder = StateGraph(State)

    graph_builder.add_node("my_tools", tool_node)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node(
        "human_confirm", get_human_confirm_node(next_node_for_yes="my_tools", next_node_for_no="chatbot", web_mode=web_mode)
    )
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("my_tools", "chatbot")

    def chatbot_route(state: State):
        """路由函数，处理工具调用"""
        try:
            if isinstance(state, list):
                ai_message = state[-1]
            elif messages := state.get("messages", []):
                ai_message = messages[-1]
            else:
                raise ValueError(f"No messages found in input state to tool_edge: {state}")

            if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                # 从配置文件获取工具分类
                safe_tools = TOOL_SECURITY_CONFIG["safe_tools"]
                shell_tools = TOOL_SECURITY_CONFIG["shell_tools"]
                confirm_required_tools = TOOL_SECURITY_CONFIG["confirm_required_tools"]
                
                # 记录工具调用信息
                tool_names = [tool_call.get("name", "unknown") for tool_call in ai_message.tool_calls]
                logger.info(f"检测到工具调用: {', '.join(tool_names)}")
                
                for tool_call in ai_message.tool_calls:
                    tool_name = tool_call.get("name", "")
                    args = tool_call.get("args", {})
                    
                    # 处理安全工具（直接执行）
                    if tool_name in safe_tools:
                        logger.info(f"安全工具调用: {tool_name}")
                        print(f"🟢 安全工具，直接执行: {tool_name}")
                        return "my_tools"
                    
                    # 处理需要确认的工具
                    elif tool_name in confirm_required_tools:
                        logger.info(f"需要确认的工具调用: {tool_name}")
                        print(f"⚠️ 需要确认的工具: {tool_name}")
                        return "human_confirm"
                    
                    # 处理shell命令工具
                    elif tool_name in shell_tools:
                        command = args.get("command", "")
                        logger.info(f"Shell命令工具调用: {tool_name}, 命令: {command}")
                        
                        # 使用缓存的白名单检查
                        if cached_is_safe_command(command):
                            print(f"🟢 白名单命令，直接执行: {command}")
                            return "my_tools"
                        else:
                            # 非白名单命令，需要用户确认
                            print(f"⚠️ 非白名单命令，需要确认: {command}")
                            return "human_confirm"
                    
                    # 其他工具默认需要确认
                    else:
                        logger.warning(f"未知工具调用: {tool_name}")
                        print(f"⚠️ 未知工具，需要确认: {tool_name}")
                        return "human_confirm"
            
            return END
            
        except Exception as e:
            logger.error(f"路由函数执行出错: {e}")
            print(f"🚫 路由处理出错: {e}")
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
