from langchain_core.tools import tool
from config.config import CONFIG
from utils.logger import log_command_execution
import subprocess
import os

@tool
def run_shell_command_popen_tool(command: str) -> str:
    """Execute shell command with directory restrictions and path validation. Input a string command and return the command output."""
    try:
        # Log command execution
        log_command_execution(command, "system", "executing")
        
        # Check directory restrictions if enabled
        if CONFIG.get("restricted_mode", False):
            try:
                from utils.path_validator import validate_command_paths, get_safe_working_directory
                
                # Validate command paths
                is_allowed, reason, detected_paths = validate_command_paths(command)
                if not is_allowed:
                    error_msg = f"🚫 Command blocked by directory restriction: {reason}"
                    log_command_execution(command, "system", "blocked", error_msg)
                    return error_msg
                
                # Use safe working directory
                cwd = get_safe_working_directory()
                if detected_paths:
                    log_command_execution(command, "system", "path_check", f"Validated paths: {', '.join(detected_paths)}")
                
            except ImportError as e:
                error_msg = f"⚠️ Path validation unavailable: {str(e)}"
                log_command_execution(command, "system", "validation_error", error_msg)
                return error_msg
        else:
            # Get working directory (normal mode)
            working_dir = CONFIG.get("working_directory", None)
            if working_dir and os.path.exists(working_dir):
                # If working directory is configured and exists, use the configured directory
                cwd = working_dir
            else:
                # Otherwise use current directory
                cwd = None
        
        # Log the working directory being used
        if cwd:
            log_command_execution(command, "system", "working_dir", f"Using working directory: {cwd}")
        
        # Execute command uniformly through shell
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
        
        # Log execution result
        log_command_execution(command, "system", status, output)
        
        return output
        
    except subprocess.TimeoutExpired:
        error_msg = f"Command timeout: {command}"
        log_command_execution(command, "system", "timeout", error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"Execution error: {str(e)}"
        log_command_execution(command, "system", "error", error_msg)
        return error_msg
