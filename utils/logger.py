import logging
from datetime import datetime
from typing import Optional
from config.config import CONFIG

# 设置日志
logging.basicConfig(
    level=getattr(logging, CONFIG["log_level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_command_execution(command: str, user: str, status: str, result: Optional[str] = None):
    """记录命令执行日志"""
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {user} | {command} | {status}"
    if result:
        # 限制结果长度，避免日志文件过大
        truncated_result = result[:200] + "..." if len(result) > 200 else result
        log_entry += f"\n | {truncated_result}"
    
    logger.info(log_entry)
    
    # 写入专门的命令日志文件
    with open(f'logs/commands_{datetime.now().strftime("%Y%m%d")}.log', 'a') as f:
        f.write(log_entry + '\n')
