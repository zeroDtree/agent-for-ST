from langchain_core.tools import tool
from config.config import CONFIG
from utils.logger import log_command_execution
import subprocess
import shlex

@tool
def run_shell_command_popen_tool(command: str) -> str:
    """执行shell命令。输入一个字符串命令，返回命令的输出。"""
    try:
        # 记录命令执行
        log_command_execution(command, "system", "executing")
        
        # 使用shlex分解命令，更安全
        command_args = shlex.split(command)
        
        # 执行命令并设置超时
        result = subprocess.run(
            command_args,
            capture_output=True,
            text=True,
            timeout=CONFIG["command_timeout"]
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nError: {result.stderr}"
        
        if result.returncode != 0:
            status = f"failed_with_code_{result.returncode}"
        else:
            status = "success"
        
        # 记录执行结果
        log_command_execution(command, "system", status, output)
        
        return output
        
    except subprocess.TimeoutExpired:
        error_msg = f"命令超时: {command}"
        log_command_execution(command, "system", "timeout", error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"执行错误: {str(e)}"
        log_command_execution(command, "system", "error", error_msg)
        return error_msg
