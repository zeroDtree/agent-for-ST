import logging
from datetime import datetime
from typing import Optional
from config.config import CONFIG

# Set up logging
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
    """Log command execution"""
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {user} | {command} | {status}"
    if result:
        # Limit result length to avoid large log files
        truncated_result = result[:200] + "..." if len(result) > 200 else result
        log_entry += f"\n | {truncated_result}"
    
    logger.info(log_entry)
    
    # Write to dedicated command log file
    with open(f'logs/commands_{datetime.now().strftime("%Y%m%d")}.log', 'a') as f:
        f.write(log_entry + '\n')
