# my package
import os

from config.config import CONFIG
from llms.llm import get_llm_model
from tools import ALL_TOOLS


def create_llm_with_tools():
    """Create LLM with tools using current configuration"""
    llm = get_llm_model(
        model_name=CONFIG["llm_model_name"],
        base_url=CONFIG["llm_base_url"],
        apikey=os.getenv(CONFIG["llm_api_key_env"]),
        max_tokens=CONFIG["llm_max_tokens"],
        streaming=CONFIG["llm_streaming"],
        temperature=CONFIG["llm_temperature"],
        presence_penalty=CONFIG["llm_presence_penalty"],
        frequency_penalty=CONFIG["llm_frequency_penalty"],
    )
    return llm.bind_tools(ALL_TOOLS)


# Create default instance using configuration
llm_with_tools = create_llm_with_tools()
