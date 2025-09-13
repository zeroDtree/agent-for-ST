from functools import lru_cache

from config.config import WHITELIST_CONFIG


@lru_cache(maxsize=WHITELIST_CONFIG["cache_size"])
def cached_is_safe_command(command: str) -> bool:
    """Cache whitelist check results"""
    from tools.whitelist import is_safe_command

    return is_safe_command(command)
