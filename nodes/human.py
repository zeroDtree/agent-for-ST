from langgraph.graph import START, END
from langgraph.types import Command
from states.state import State
from langchain_core.messages import ToolMessage
import threading
import time
from utils.logger import logger


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
    """控制台模式的确认"""
    print(tool_call_message)
    human_str = input(f"接下来将执行{tool_call_message.content}，\n是否执行？ (yes/no)：")
    if human_str in ["y", "Y", "yes", "Yes", "YES"]:
        return Command(goto=next_node_for_yes)
    else:
        # 当用户拒绝时，添加工具响应消息表示拒绝
        messages = state["messages"]
        tool_messages = []
        for tool_call in tool_call_message.tool_calls:
            tool_message = ToolMessage(
                content="用户拒绝执行此工具调用",
                tool_call_id=tool_call["id"]
            )
            tool_messages.append(tool_message)
        
        return Command(goto=next_node_for_no, update={"messages": tool_messages})


def web_confirm(state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
    """Web模式的确认 - 通过API接口与前端交互"""
    # 获取全局的pending_confirmations（需要在web_server中定义）
    try:
        # 动态导入，避免循环导入
        import web_server
        pending_confirmations = web_server.pending_confirmations
    except ImportError:
        logger.error("Web模式确认需要web_server模块")
        return console_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)
    
    # 提取命令信息
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
    
    # 生成会话ID（这里简化处理，实际应用中可以从请求中获取）
    session_id = getattr(state, 'session_id', 'default')
    
    # 创建确认事件
    confirmation_event = threading.Event()
    confirmation_result = {"confirmed": False}
    
    def confirmation_callback(confirmed: bool):
        confirmation_result["confirmed"] = confirmed
        confirmation_event.set()
    
    # 添加到待确认列表
    pending_confirmations[session_id] = {
        "command": command_info,
        "tool_name": tool_name,
        "callback": confirmation_callback
    }
    
    # 通过SSE推送确认请求
    try:
        web_server.send_sse_event(session_id, {
            "type": "confirmation_request",
            "command": command_info,
            "tool_name": tool_name,
            "session_id": session_id
        })
        logger.info(f"已通过SSE推送确认请求: {command_info}")
    except Exception as e:
        logger.warning(f"SSE推送失败，将依赖轮询机制: {e}")
    
    logger.info(f"等待Web前端确认命令: {command_info}")
    
    # 等待前端确认（设置超时）
    timeout = 300  # 5分钟超时
    if confirmation_event.wait(timeout):
        # 用户已做出选择
        if confirmation_result["confirmed"]:
            logger.info(f"用户确认执行命令: {command_info}")
            return Command(goto=next_node_for_yes)
        else:
            logger.info(f"用户拒绝执行命令: {command_info}")
            # 添加拒绝消息
            tool_messages = []
            for tool_call in tool_call_message.tool_calls:
                tool_message = ToolMessage(
                    content="用户拒绝执行此工具调用",
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)
            
            return Command(goto=next_node_for_no, update={"messages": tool_messages})
    else:
        # 超时处理
        logger.warning(f"命令确认超时: {command_info}")
        # 清理待确认状态
        if session_id in pending_confirmations:
            del pending_confirmations[session_id]
        
        # 添加超时消息
        tool_messages = []
        for tool_call in tool_call_message.tool_calls:
            tool_message = ToolMessage(
                content="命令确认超时，已自动拒绝执行",
                tool_call_id=tool_call["id"]
            )
            tool_messages.append(tool_message)
        
        return Command(goto=next_node_for_no, update={"messages": tool_messages})
