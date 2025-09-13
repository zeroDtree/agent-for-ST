# Import all tools
from .codebase import get_codebase_stats, search_codebase, update_codebase_index
from .embedding_knowledge_base import (
    add_text_to_knowledge_base,
    get_knowledge_base_stats,
    list_knowledge_bases,
    search_knowledge_base,
)
from .shell import run_shell_command_popen_tool
from .whitelist import is_safe_command

# Tool list for easy extension
ALL_TOOLS = [
    run_shell_command_popen_tool,
    # Codebase search tools
    search_codebase,
    update_codebase_index,
    get_codebase_stats,
    # Embedding knowledge base tools
    search_knowledge_base,
    add_text_to_knowledge_base,
    get_knowledge_base_stats,
    list_knowledge_bases,
]

__all__ = [
    "run_shell_command_popen_tool",
    "is_safe_command",
    # Codebase search tools
    "search_codebase",
    "update_codebase_index",
    "get_codebase_stats",
    # Embedding knowledge base tools
    "search_knowledge_base",
    "add_text_to_knowledge_base",
    "get_knowledge_base_stats",
    "list_knowledge_bases",
    "ALL_TOOLS",
]
