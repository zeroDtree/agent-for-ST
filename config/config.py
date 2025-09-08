from datetime import datetime
from typing import Dict, Any

# 主配置
CONFIG: Dict[str, Any] = {
    "thread_id": "1",
    "recursion_limit": 1000,
    "stream_mode": "values",
    "max_history_messages": 10000,
    "command_timeout": 30,
    "log_level": "INFO",
    # 工作目录配置
    "working_directory": None,  # Agent的初始工作目录，None表示使用当前目录
    # 博客知识库配置
    "blog_path": "data/blog_content",
    "vector_db_path": "data/vector_db",
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 轻量的多语言embedding模型
    "chunk_size": 2000,  # 减小chunk大小，提高语义聚焦度
    "chunk_overlap": 100,  # 相应减小重叠
    "search_k": 10,  # 初步搜索更多结果
    "rerank_top_k": 5,  # 重排序后返回的结果数
}

# 白名单配置
WHITELIST_CONFIG = {"cache_size": 1000, "cache_ttl": 300}  # 5分钟

# 监控配置
MONITOR_CONFIG = {"enable_performance_monitoring": True, "slow_threshold_ms": 10000}  # 10秒

# 工具安全配置
TOOL_SECURITY_CONFIG = {
    # 安全工具列表（无需用户确认）
    "safe_tools": {"update_blog_knowledge_base", "search_blog_knowledge_base", "get_blog_knowledge_base_stats"},
    # Shell命令工具列表
    "shell_tools": {"run_shell_command_popen_tool"},
    # 需要确认的工具列表
    "confirm_required_tools": {
        # 可以在这里添加其他需要确认的工具
    },
}
