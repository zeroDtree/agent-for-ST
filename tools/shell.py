from langchain_core.tools import tool
from config.config import CONFIG
from utils.logger import log_command_execution
import subprocess
import os

@tool
def run_shell_command_popen_tool(command: str) -> str:
    """执行shell命令。输入一个字符串命令，返回命令的输出。"""
    try:
        # 记录命令执行
        log_command_execution(command, "system", "executing")
        
        # 获取工作目录
        working_dir = CONFIG.get("working_directory", None)
        if working_dir and os.path.exists(working_dir):
            # 如果配置了工作目录且存在，则使用配置的目录
            cwd = working_dir
        else:
            # 否则使用当前目录
            cwd = None
        
        # 统一通过shell执行命令
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=CONFIG["command_timeout"],
            cwd=cwd
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
