# my package
from llms.llm import get_llm_model
from tools import ALL_TOOLS


llm = get_llm_model("deepseek-chat")
llm_with_tools = llm.bind_tools(ALL_TOOLS)
