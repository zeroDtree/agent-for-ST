# my package
from llms.llm import get_llm_model
from tools.shell import run_shell_command_popen_tool


llm = get_llm_model("deepseek-chat")
llm_with_tools = llm.bind_tools([run_shell_command_popen_tool])
