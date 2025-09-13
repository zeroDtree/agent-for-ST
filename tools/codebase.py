"""
Semantic codebase search tool
Search for code patterns, functions, classes, and implementations using natural language
"""

from typing import Optional

from langchain_core.tools import tool

from config.config import CONFIG
from tools.embedding_knowledge_base import get_knowledge_base
from utils.constants import CODE_FILE_PATTERNS
from utils.logger import get_and_create_new_log_dir, get_logger

log_dir = get_and_create_new_log_dir(root=CONFIG["log_dir"], prefix="", suffix="", strftime_format="%Y%m%d")
logger = get_logger(name=__name__, log_dir=log_dir)


@tool
def search_codebase(
    query: str,
    language_filter: Optional[str] = None,
    limit: int = 5,
) -> str:
    """Search codebase using semantic understanding

    This tool searches through the 'code' knowledge base using natural language queries.
    It understands code semantics, patterns, and can find relevant implementations.
    The knowledge base is managed by manage_kb and contains indexed source code files.

    Args:
        query: Natural language search query (e.g., "authentication logic", "error handling patterns", "database connections")
        language_filter: Filter by programming language (e.g., "python", "javascript", "java")
        limit: Maximum number of results to return (default: 5)

    Examples:
        - search_codebase("user authentication flow")
        - search_codebase("error handling patterns", language_filter="python")
        - search_codebase("database connection setup")
        - search_codebase("API endpoint definitions")
    """
    try:
        # Use fixed knowledge base name 'code'
        kb_name = "code"

        # Get the 'code' knowledge base (managed by manage_kb)
        kb = get_knowledge_base(name=kb_name)

        # Build search filter for language if specified
        search_filter = None
        if language_filter:
            search_filter = {"language": language_filter.lower()}

        # Perform semantic search
        results = kb.search(query, k=limit, filter_metadata=search_filter)

        if not results:
            lang_msg = f" (language: {language_filter})" if language_filter else ""
            return f"🔍 No code found matching '{query}'{lang_msg} in the code knowledge base"

        # Format results for code search
        response = f"🔍 Found {len(results)} code matches for '{query}':\n\n"

        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            content = result["content"]
            score = result["score"]
            relevance_score = result.get("relevance_score", score)

            # Extract code-specific metadata
            language = metadata.get("language", "unknown")
            metadata.get("file_type", "")
            lines = metadata.get("lines", "unknown")
            size = metadata.get("size", "unknown")
            code_stats = metadata.get("code_stats", {})

            response += f"**{i}. {metadata.get('title', 'Unnamed file')}**\n"
            response += f"📁 File: {metadata.get('source', 'Unknown')}\n"
            response += f"💻 Language: {language.title()}\n"
            response += f"📏 Lines: {lines} | Size: {size} bytes\n"

            # Show code statistics if available
            if code_stats:
                stats_parts = []
                if code_stats.get("functions", 0) > 0:
                    stats_parts.append(f"Functions: {code_stats['functions']}")
                if code_stats.get("classes", 0) > 0:
                    stats_parts.append(f"Classes: {code_stats['classes']}")
                if code_stats.get("imports", 0) > 0:
                    stats_parts.append(f"Imports: {code_stats['imports']}")

                if stats_parts:
                    response += f"📊 Code stats: {' | '.join(stats_parts)}\n"

            response += f"🎯 Relevance: {relevance_score:.3f} | Vector similarity: {score:.3f}\n"

            # Show code preview (truncated for readability)
            preview_lines = content.splitlines()[:30]  # First 30 lines
            preview = "\n".join(preview_lines)
            if len(content.splitlines()) > 30:
                preview += f"\n... ({len(content.splitlines()) - 30} more lines)"

            response += f"📄 Code preview:\n```{language}\n{preview}\n```\n\n"
            response += "---\n\n"

        # Add search summary
        response += f"**Search Summary:**\n"
        response += f"- Knowledge base: {kb_name}\n"
        if language_filter:
            response += f"- Language filter: {language_filter}\n"

        return response

    except Exception as e:
        logger.error(f"Error in codebase search: {e}")
        return f"❌ Codebase search failed: {str(e)}"


@tool
def update_codebase_index() -> str:
    """Update the codebase search index

    Updates the 'code' knowledge base managed by manage_kb.
    Use this when you've made significant changes to the codebase.
    Note: The actual indexing configuration (paths, patterns) should be
    managed through manage_kb commands.
    """
    try:
        # Use fixed knowledge base name 'code'
        kb_name = "code"
        kb = get_knowledge_base(name=kb_name)

        # Update the knowledge base
        result = kb.update_knowledge_base(file_patterns=CODE_FILE_PATTERNS)

        if result.get("success", True):
            response = f"✅ Codebase index updated successfully!\n\n"
            response += f"📄 Files processed: {result.get('total_files_processed', 'unknown')}\n"
            response += f"📊 Document chunks: {result.get('new_documents_count', 'unknown')}\n"
            response += f"🔄 Updated files: {len(result.get('updated_files', []))}\n"

            return response
        else:
            return f"❌ Failed to update codebase index: {result.get('message', 'Unknown error')}"

    except Exception as e:
        logger.error(f"Error updating codebase index: {e}")
        return f"❌ Index update failed: {str(e)}"


@tool
def get_codebase_stats() -> str:
    """Get statistics about the indexed codebase

    Returns statistics for the 'code' knowledge base managed by manage_kb.
    """
    try:
        # Use fixed knowledge base name 'code'
        kb_name = "code"
        kb = get_knowledge_base(name=kb_name)

        stats = kb.get_stats()

        if "error" in stats:
            return f"❌ Failed to get codebase statistics: {stats['error']}"

        response = f"📊 Codebase statistics for '{kb_name}' knowledge base:\n\n"
        response += f"📄 Total documents: {stats['total_documents']}\n"
        response += f"📁 Total files: {stats['total_files']}\n"
        response += f"🗂️ Database path: {stats['vector_db_path']}\n"
        response += f"🕒 Last updated: {stats['last_updated']}\n"

        if stats.get("file_types"):
            response += f"\n📋 File types breakdown:\n"
            for ext, count in stats["file_types"].items():
                response += f"  • {ext}: {count} files\n"

        response += f"\n📂 Source paths: {', '.join(stats['source_paths'])}"

        return response

    except Exception as e:
        logger.error(f"Error getting codebase stats: {e}")
        return f"❌ Failed to get statistics: {str(e)}"
