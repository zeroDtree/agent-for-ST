from typing import Any, Dict

# Main configuration
CONFIG: Dict[str, Any] = {
    "thread_id": "1",
    "recursion_limit": 1000,
    "stream_mode": "values",
    "max_history_messages": 10000,
    "command_timeout": 30,
    "log_dir": "logs",
    "log_level": "INFO",
    # Working directory configuration
    # Agent's initial working directory, None means use current directory
    "working_directory": None,
    # Directory restriction configuration (for debugging mode)
    "restricted_mode": False,  # Enable directory restriction mode
    # Restrict AI operations to this directory and its subdirectories
    "allowed_directory": None,
    # Allow reading files from parent directories (read-only)
    "allow_parent_read": False,
    # Enforce strict sandboxing (no operations outside allowed directory)
    "enforce_strict_sandbox": True,
    # Auto mode configuration
    # Options: "manual", "blacklist_reject", "universal_reject",
    # "whitelist_accept", "universal_accept"
    "auto_mode": "manual",
    # LLM configuration
    "llm_model_name": "deepseek-chat",  # Default model name
    "llm_base_url": "https://api.deepseek.com/v1",  # Default API base URL
    "llm_api_key_env": "DEEPSEEK_API_KEY",  # Environment variable name for API key
    "llm_max_tokens": 8192,  # Maximum tokens for LLM response
    "llm_streaming": True,  # Enable streaming responses
    "llm_temperature": 1.0,  # Temperature for response generation
    "llm_presence_penalty": 0.0,  # Presence penalty
    "llm_frequency_penalty": 0.0,  # Frequency penalty
    # Knowledge base configuration
    # Default source path for knowledge base (current directory)
    "default_source_path": ".",
    "vector_db_path": "data/vector_db",
    # Lightweight multilingual embedding model
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "chunk_size": 2000,  # Reduce chunk size to improve semantic focus
    "chunk_overlap": 100,  # Correspondingly reduce overlap
    "search_k": 10,  # Initial search for more results
    "rerank_top_k": 5,  # Number of results returned after reranking
}

# Whitelist configuration
WHITELIST_CONFIG = {"cache_size": 1000, "cache_ttl": 300}  # 5 minutes

# Monitoring configuration
MONITOR_CONFIG = {
    "enable_performance_monitoring": True,
    "slow_threshold_ms": 10000,
}  # 10 seconds

# Tool security configuration
TOOL_SECURITY_CONFIG = {
    # Safe tools list (no user confirmation required)
    "safe_tools": {
        "search_knowledge_base",
        "add_text_to_knowledge_base",
        "get_knowledge_base_stats",
        "list_knowledge_bases",
    },
    # Shell command tools list
    "shell_tools": {"run_shell_command_popen_tool"},
    # Tools requiring confirmation list
    "confirm_required_tools": {
        # You can add other tools requiring confirmation here
    },
}
