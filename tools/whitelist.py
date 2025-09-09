# Command whitelist configuration
# These commands are considered safe and can be executed directly without user confirmation

SAFE_COMMANDS = {
    # File system operations
    "ls",
    "dir",
    "pwd",
    "cd",
    "mkdir",
    "rmdir",
    "touch",
    # File viewing and searching
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "grep",
    "find",
    "locate",
    "awk",
    "sed",
    # System information
    "whoami",
    "hostname",
    "uname",
    "uptime",
    "ps",
    "top",
    "htop",
    # Network related
    "ping",
    "curl",
    "wget",
    "netstat",
    "ss",
    "ip",
    "ifconfig",
    # Package management (read-only operations)
    "dpkg",
    "rpm",
    "pacman",
    "apt",
    "yum",
    "brew",
    # Debug and development tools (safe read-only operations)
    "file",
    "stat",
    "du",
    "diff",
    "cmp",
    "hexdump",
    "od",
    "strings",
    "tree",
    "ldd",
    "nm",
    "objdump",
    "readelf",
    "size",
    "md5sum",
    "sha256sum",
    "sha1sum",
    # Text processing for debugging
    "sort",
    "uniq",
    "cut",
    "tr",
    "column",
    "paste",
    "join",
    "comm",
    "tac",
    "rev",
    # Other safe commands
    "echo",
    "date",
    "cal",
    "bc",
    "wc",
    "which",
    "whereis",
    "type",
    "alias",
    "history",
    "clear",
    # Environment variables
    "env",
    "export",
    "set",
    "printenv",
    # Compression and decompression (read-only)
    "tar",
    "gzip",
    "gunzip",
    "zip",
    "unzip",
    # Safe programming language tools (read-only operations)
    "python3",
    "python",
    "node",
    "npm",
    "pip",
}

# Dangerous command blacklist (will be rejected even if included in whitelist)
DANGEROUS_COMMANDS = {
    "del",
    "format",
    "dd",
    "mkfs",
    "fdisk",
    "parted",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "useradd",
    "userdel",
    "usermod",
    "groupadd",
    "groupdel",
    "chmod",
    "chown",
    "chgrp",
    "sudo",
    "su",
    "kill",
    "killall",
    "pkill",
    "xkill",
    "mount",
    "umount",
    "fstab",
    "iptables",
    "firewall-cmd",
    "ufw",
    "crontab",
    "at",
    "systemctl",
    "service",
    "passwd",
    "ssh-keygen",
    "openssl",
    "mysql",
    "psql",
    "sqlite3",
    "git",
    "svn",
    "hg",  # Version control may modify code
    "wget",
    "curl",  # Downloads may be unsafe
    "scp",
    "rsync",
    "sftp",  # File transfer
    "ssh",
    "telnet",
    "nc",
    "netcat",  # Network connections
    # Removed python, node, npm, pip from dangerous list as they can be safe for debugging in restricted mode
    "bash",
    "sh",
    "zsh",
    "fish",  # Shell execution
    "vim",
    "nano",
    "emacs",  # Editors
    "nmap",
    "traceroute",
    "dig",
    "nslookup",  # Network probing
}


def is_safe_command(command: str) -> bool:
    """
    Check if command is in whitelist and not in blacklist

    Args:
        command: Command string to check

    Returns:
        bool: True if command is safe, False otherwise
    """
    # Extract basic part of command (first word)
    command_parts = command.strip().split()
    if not command_parts:
        return False

    base_command = command_parts[0].lower()

    # Check if in blacklist
    if base_command in DANGEROUS_COMMANDS:
        return False

    # Check if in whitelist
    return base_command in SAFE_COMMANDS


def is_safe_command_with_restrictions(command: str) -> bool:
    """
    Check if command is safe considering directory restrictions
    
    Args:
        command: Command string to check
        
    Returns:
        bool: True if command is safe under current restrictions, False otherwise
    """
    from config.config import CONFIG
    
    # First check basic safety
    if not is_safe_command(command):
        return False
    
    # If not in restricted mode, use regular whitelist check
    if not CONFIG.get("restricted_mode", False):
        return True
    
    # In restricted mode, perform additional path validation
    try:
        from utils.path_validator import validate_command_paths
        is_allowed, reason, paths = validate_command_paths(command)
        return is_allowed
    except ImportError:
        # Fallback to basic check if path validator is not available
        return True


def get_command_category(command: str) -> str:
    """
    Get command category

    Args:
        command: Command string

    Returns:
        str: Command category
    """
    command_parts = command.strip().split()
    if not command_parts:
        return "unknown"

    base_command = command_parts[0].lower()

    if base_command in DANGEROUS_COMMANDS:
        return "dangerous"
    elif base_command in SAFE_COMMANDS:
        return "safe"
    else:
        return "unknown"


def should_auto_approve_command(command: str) -> tuple[bool, str]:
    """
    Check if command should be auto-approved based on current auto mode
    
    Args:
        command: Command to check
        
    Returns:
        tuple[bool, str]: (should_auto_approve, reason)
    """
    from config.config import CONFIG
    
    auto_mode = CONFIG.get("auto_mode", "manual")
    
    if auto_mode == "manual":
        return False, "Manual mode - requires human confirmation"
    
    # Get command safety info
    is_safe = is_safe_command(command)
    category = get_command_category(command)
    
    if auto_mode == "blacklist_reject":
        # Auto reject blacklist commands, manual for others
        if category == "dangerous":
            return False, "Auto-rejected: dangerous command in blacklist"
        return False, "Blacklist reject mode - non-blacklist commands need manual confirmation"
    
    elif auto_mode == "universal_reject":
        # Auto reject all commands requiring confirmation
        return False, "Auto-rejected: universal reject mode"
    
    elif auto_mode == "whitelist_accept":
        # Auto accept non-blacklist commands (whitelist + unknown)
        if category == "dangerous":
            return False, "Auto-rejected: dangerous command in blacklist"
        return True, f"Auto-approved: non-blacklist command ({category})"
    
    elif auto_mode == "universal_accept":
        # Auto accept all commands (including blacklist)
        return True, f"Auto-approved: universal accept mode ({category})"
    
    else:
        return False, f"Unknown auto mode: {auto_mode}"


def get_auto_mode_description() -> str:
    """
    Get description of current auto mode
    
    Returns:
        str: Description of current auto mode
    """
    from config.config import CONFIG
    
    auto_mode = CONFIG.get("auto_mode", "manual")
    
    descriptions = {
        "manual": "🤚 Manual Mode - All commands require human confirmation",
        "blacklist_reject": "🚫 Blacklist Reject - Auto-reject dangerous commands, manual for others",
        "universal_reject": "⛔ Universal Reject - Auto-reject all commands requiring confirmation",
        "whitelist_accept": "✅ Whitelist Accept - Auto-accept non-blacklist commands",
        "universal_accept": "🟢 Universal Accept - Auto-accept ALL commands (including dangerous ones)"
    }
    
    return descriptions.get(auto_mode, f"❓ Unknown mode: {auto_mode}")
