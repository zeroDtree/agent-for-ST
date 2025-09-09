from typing import List
from langchain_core.messages import BaseMessage
from config.config import CONFIG

def cleanup_old_messages(messages: List[BaseMessage], max_history: int = None) -> List[BaseMessage]:
    """Clean up old conversation history"""
    if max_history is None:
        max_history = CONFIG["max_history_messages"]
    
    if len(messages) > max_history:
        # Keep the most recent max_history messages
        return messages[-max_history:]
    return messages
