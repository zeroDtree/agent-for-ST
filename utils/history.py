from typing import List
from langchain_core.messages import BaseMessage
from config.config import CONFIG

def cleanup_old_messages(messages: List[BaseMessage], max_history: int = None) -> List[BaseMessage]:
    """清理旧的会话历史"""
    if max_history is None:
        max_history = CONFIG["max_history_messages"]
    
    if len(messages) > max_history:
        # 保留最近的max_history条消息
        return messages[-max_history:]
    return messages
