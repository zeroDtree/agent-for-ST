import time
from config.config import MONITOR_CONFIG
from utils.logger import logger

def monitor_performance(func):
    """Performance monitoring decorator"""
    def wrapper(*args, **kwargs):
        if not MONITOR_CONFIG["enable_performance_monitoring"]:
            return func(*args, **kwargs)
            
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        
        if duration_ms > MONITOR_CONFIG["slow_threshold_ms"]:
            logger.warning(f"Slow operation: {func.__name__} took {duration_ms:.2f}ms")
        else:
            logger.debug(f"{func.__name__} took {duration_ms:.2f}ms")
            
        return result
    return wrapper
