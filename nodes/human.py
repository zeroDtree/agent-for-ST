from langgraph.graph import START, END
from langgraph.types import Command
from states.state import State
from langchain_core.messages import ToolMessage


def get_human_confirm_node(next_node_for_yes: str, next_node_for_no: str):
    def human_confirm(state: State):
        tool_call_message = state["messages"][-1]
        nonlocal next_node_for_yes
        nonlocal next_node_for_no
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

    return human_confirm
