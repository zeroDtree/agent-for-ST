from datetime import datetime
from typing import Dict, Any

# 主配置
CONFIG: Dict[str, Any] = {
    "thread_id": "1",
    "recursion_limit": 1000,
    "stream_mode": "values",
    "max_history_messages": 10000,
    "command_timeout": 30,
    "log_level": "INFO"
}

# 白名单配置
WHITELIST_CONFIG = {
    "cache_size": 1000,
    "cache_ttl": 300  # 5分钟
}

# 监控配置
MONITOR_CONFIG = {
    "enable_performance_monitoring": True,
    "slow_threshold_ms": 10000  # 10秒
}
