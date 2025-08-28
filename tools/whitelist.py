# 命令白名单配置
# 这些命令被认为是安全的，不需要用户确认就可以直接执行

SAFE_COMMANDS = {
    # 文件系统操作
    "ls",
    "dir",
    "pwd",
    "cd",
    "mkdir",
    "rmdir",
    # 文件查看和搜索
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "grep",
    "find",
    "locate",
    # 系统信息
    "whoami",
    "hostname",
    "uname",
    "uptime",
    "ps",
    "top",
    "htop",
    # 网络相关
    "ping",
    "curl",
    "wget",
    "netstat",
    "ss",
    "ip",
    "ifconfig",
    # 包管理（只读操作）
    "dpkg",
    "rpm",
    "pacman",
    "apt",
    "yum",
    "brew",
    # 其他安全命令
    "echo",
    "date",
    "cal",
    "bc",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "which",
    "whereis",
    "type",
    "alias",
    "history",
    "clear",
    # 环境变量
    "env",
    "export",
    "set",
    "printenv",
    # 压缩解压（只读）
    "tar",
    "gzip",
    "gunzip",
    "zip",
    "unzip",
}

# 危险命令黑名单（即使包含在白名单中也会被拒绝）
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
    "hg",  # 版本控制可能修改代码
    "wget",
    "curl",  # 下载可能不安全
    "scp",
    "rsync",
    "sftp",  # 文件传输
    "ssh",
    "telnet",
    "nc",
    "netcat",  # 网络连接
    "python",
    "python3",
    "node",
    "npm",
    "pip",  # 脚本执行
    "bash",
    "sh",
    "zsh",
    "fish",  # shell执行
    "vim",
    "nano",
    "emacs",  # 编辑器
    "nmap",
    "traceroute",
    "dig",
    "nslookup",  # 网络探测
}


def is_safe_command(command: str) -> bool:
    """
    检查命令是否在白名单中且不在黑名单中

    Args:
        command: 要检查的命令字符串

    Returns:
        bool: 如果命令安全返回True，否则返回False
    """
    # 提取命令的基本部分（第一个单词）
    command_parts = command.strip().split()
    if not command_parts:
        return False

    base_command = command_parts[0].lower()

    # 检查是否在黑名单中
    if base_command in DANGEROUS_COMMANDS:
        return False

    # 检查是否在白名单中
    return base_command in SAFE_COMMANDS


def get_command_category(command: str) -> str:
    """
    获取命令的分类

    Args:
        command: 命令字符串

    Returns:
        str: 命令分类
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
