"""
Path validation utilities for directory restriction and sandboxing
"""

import os
import re
from typing import Optional, Tuple, List
from config.config import CONFIG
from utils.logger import logger


def normalize_path(path: str) -> str:
    """
    Normalize a path by resolving relative paths and symlinks

    Args:
        path: Path to normalize

    Returns:
        str: Normalized absolute path
    """
    return os.path.realpath(os.path.abspath(path))


def is_path_allowed(target_path: str, operation_type: str = "read") -> Tuple[bool, str]:
    """
    Check if a path operation is allowed under current restrictions

    Args:
        target_path: Path to check
        operation_type: Type of operation ('read', 'write', 'execute')

    Returns:
        Tuple[bool, str]: (is_allowed, reason)
    """
    if not CONFIG.get("restricted_mode", False):
        return True, "Restriction mode disabled"

    allowed_dir = CONFIG.get("allowed_directory")
    if not allowed_dir:
        return True, "No directory restriction configured"

    try:
        # Normalize both paths
        normalized_target = normalize_path(target_path)
        normalized_allowed = normalize_path(allowed_dir)

        # Check if target is within allowed directory
        is_within_allowed = (
            normalized_target.startswith(normalized_allowed + os.sep) or normalized_target == normalized_allowed
        )

        if is_within_allowed:
            return True, f"Path within allowed directory: {normalized_allowed}"

        # Special case: allow reading parent directories if configured
        if operation_type == "read" and CONFIG.get("allow_parent_read", False):
            # Check if target is a parent of allowed directory
            if normalized_allowed.startswith(normalized_target + os.sep):
                return True, f"Parent directory read allowed: {normalized_target}"

        # Strict sandbox mode
        if CONFIG.get("enforce_strict_sandbox", True):
            return False, f"Path outside allowed directory: {normalized_target} not in {normalized_allowed}"

        return False, f"Path restriction violation: {normalized_target}"

    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return False, f"Path validation error: {str(e)}"


def extract_paths_from_command(command: str) -> List[str]:
    """
    Extract potential file/directory paths from a command

    Args:
        command: Shell command to analyze

    Returns:
        List[str]: List of detected paths
    """
    paths = []

    # Common patterns for file paths in commands
    path_patterns = [
        r"(?:^|\s)([^\s]*\.(?:py|js|ts|txt|json|yaml|yml|md|sh|conf|cfg|ini|log|csv)(?:\s|$))",  # File extensions
        r"(?:^|\s)([~/][^\s]*)",  # Absolute paths starting with / or ~
        r"(?:^|\s)(\.[^\s]*)",  # Relative paths starting with .
        r"(?:^|\s)([a-zA-Z0-9_.-]+/[^\s]*)",  # Directory-like paths
    ]

    for pattern in path_patterns:
        matches = re.findall(pattern, command)
        paths.extend([match.strip() for match in matches if match.strip()])

    # Remove duplicates while preserving order
    unique_paths = []
    for path in paths:
        if path not in unique_paths:
            unique_paths.append(path)

    return unique_paths


def validate_command_paths(command: str) -> Tuple[bool, str, List[str]]:
    """
    Validate all paths in a command against current restrictions

    Args:
        command: Shell command to validate

    Returns:
        Tuple[bool, str, List[str]]: (is_allowed, reason, detected_paths)
    """
    if not CONFIG.get("restricted_mode", False):
        return True, "Restriction mode disabled", []

    detected_paths = extract_paths_from_command(command)

    if not detected_paths:
        return True, "No paths detected in command", []

    # Determine operation type based on command
    operation_type = get_command_operation_type(command)

    for path in detected_paths:
        # Skip checking non-existent paths for some read operations
        if operation_type == "read" and not os.path.exists(path):
            continue

        allowed, reason = is_path_allowed(path, operation_type)
        if not allowed:
            return False, f"Path restriction violation for '{path}': {reason}", detected_paths

    return True, "All paths allowed", detected_paths


def get_command_operation_type(command: str) -> str:
    """
    Determine the primary operation type of a command

    Args:
        command: Shell command to analyze

    Returns:
        str: Operation type ('read', 'write', 'execute')
    """
    command_lower = command.lower().strip()
    command_parts = command_lower.split()

    if not command_parts:
        return "execute"

    base_command = command_parts[0]

    # Read operations
    read_commands = {
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "grep",
        "find",
        "locate",
        "ls",
        "dir",
        "pwd",
        "stat",
        "file",
        "du",
        "wc",
        "sort",
        "uniq",
    }

    # Write operations
    write_commands = {"touch", "mkdir", "rmdir", "rm", "mv", "cp", "chmod", "chown", "echo", "tee", "sed", "awk"}

    if base_command in read_commands:
        return "read"
    elif base_command in write_commands:
        return "write"
    else:
        return "execute"


def get_safe_working_directory() -> Optional[str]:
    """
    Get the safe working directory for command execution

    Returns:
        Optional[str]: Safe working directory path, or None if unrestricted
    """
    if not CONFIG.get("restricted_mode", False):
        return CONFIG.get("working_directory")

    allowed_dir = CONFIG.get("allowed_directory")
    if allowed_dir and os.path.exists(allowed_dir):
        return normalize_path(allowed_dir)

    return CONFIG.get("working_directory")


def format_restriction_info() -> str:
    """
    Format current restriction settings for display

    Returns:
        str: Formatted restriction information
    """
    if not CONFIG.get("restricted_mode", False):
        return "🔓 Directory restriction: Disabled"

    allowed_dir = CONFIG.get("allowed_directory")
    if not allowed_dir:
        return "🔓 Directory restriction: Enabled but no directory specified"

    info_lines = [
        f"🔒 Directory restriction: Enabled",
        f"📁 Allowed directory: {allowed_dir}",
        f"👀 Parent read allowed: {'Yes' if CONFIG.get('allow_parent_read', False) else 'No'}",
        f"🛡️ Strict sandbox: {'Yes' if CONFIG.get('enforce_strict_sandbox', True) else 'No'}",
    ]

    return "\n".join(info_lines)
