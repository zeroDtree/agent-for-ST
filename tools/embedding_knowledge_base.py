"""
Generic embedding knowledge base system
Convert various document types to vector database for AI retrieval
"""

from typing import Dict, List, Optional, Union

from langchain_core.tools import tool

from config.config import CONFIG
from utils.doc_processor import DocumentProcessor
from utils.ekb import EmbeddingKnowledgeBase
from utils.logger import get_logger
from utils.regex_pattern_filter import FilterOrder

logger = get_logger(__name__)

# Global knowledge base instances
_knowledge_bases: Dict[str, EmbeddingKnowledgeBase] = {}


def get_knowledge_base(
    name: str = "default",
    source_paths: Optional[Union[str, List[str]]] = None,
    custom_processors: Optional[List[DocumentProcessor]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    filter_order: FilterOrder = FilterOrder.EXCLUDE_FIRST,
    use_gitignore: bool = True,
    db_type: str = "chroma",
    debug_mode: bool = False,
) -> EmbeddingKnowledgeBase:
    """Get or create knowledge base instance"""
    global _knowledge_bases

    vector_db_path = CONFIG.get("vector_db_path", "data/vector_db")
    kb = EmbeddingKnowledgeBase(
        source_paths=source_paths,
        vector_db_path=vector_db_path,
        name=name,
        custom_processors=custom_processors,
        exclude_patterns=exclude_patterns,
        include_patterns=include_patterns,
        filter_order=filter_order,
        use_gitignore=use_gitignore,
        db_type=db_type,
        debug_mode=debug_mode,
    )

    _knowledge_bases[name] = kb

    return _knowledge_bases[name]


@tool
def search_knowledge_base(query: str, name: str = "default", limit: int = 5) -> str:
    """Search for relevant content in knowledge base

    Args:
        query: Search query
        name: Name of the knowledge base (default: "default")
        limit: Limit on number of results returned
    """
    try:
        kb = get_knowledge_base(name)
        logger.info(f"kb source paths: {kb.source_paths}")
        results = kb.search(query, k=limit)

        if not results:
            return f"🔍 No content related to '{query}' found in knowledge base '{name}'"

        response = f"🔍 Found {len(results)} relevant results in '{name}':\n\n"

        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            content = result["content"]
            score = result["score"]
            relevance_score = result.get("relevance_score", score)

            response += f"**{i}. {metadata.get('title', 'No title')}**\n"
            response += f"📁 File: {metadata.get('source', 'Unknown')}\n"

            if metadata.get("date"):
                response += f"📅 Date: {metadata.get('date')}\n"
            if metadata.get("author"):
                response += f"👤 Author: {metadata.get('author')}\n"
            if metadata.get("tags"):
                response += f"🏷️ Tags: {metadata.get('tags')}\n"
            if metadata.get("categories"):
                response += f"📂 Categories: {metadata.get('categories')}\n"

            response += f"📊 Vector similarity: {score:.3f}\n"
            response += f"🎯 Comprehensive relevance: {relevance_score:.3f}\n"
            response += f"📄 Content:\n{content}\n\n"
            response += "---\n\n"

        return response
    except Exception as e:
        logger.error(f"Error searching knowledge base '{name}': {e}")
        return f"❌ Error during search in '{name}': {str(e)}"


@tool
def add_text_to_knowledge_base(name: str, texts: str, titles: str = "") -> str:
    """Add text content directly to knowledge base

    Args:
        name: Name of the knowledge base
        texts: Pipe-separated list of text content to add
        titles: Pipe-separated list of titles for each text (optional)
    """
    try:
        kb = get_knowledge_base(name)

        text_list = [t.strip() for t in texts.split("|")]
        title_list = [t.strip() for t in titles.split("|")] if titles else []

        # Prepare metadata
        metadatas = []
        for i, _ in enumerate(text_list):
            metadata = {}
            if i < len(title_list) and title_list[i]:
                metadata["title"] = title_list[i]
            metadatas.append(metadata)

        result = kb.add_documents_from_texts(text_list, metadatas)

        if result["success"]:
            return (
                f"✅ Added {len(text_list)} text documents to knowledge base '{name}'!\n"
                f"📄 New document chunks: {result['new_documents_count']}"
            )
        else:
            return f"❌ Failed to add texts to knowledge base '{name}': {result['message']}"
    except Exception as e:
        logger.error(f"Error adding texts to knowledge base '{name}': {e}")
        return f"❌ Error adding texts to knowledge base '{name}': {str(e)}"


@tool
def get_knowledge_base_stats(name: str = "default") -> str:
    """Get knowledge base statistics

    Args:
        name: Name of the knowledge base (default: "default")
    """
    try:
        kb = get_knowledge_base(name)
        stats = kb.get_stats()

        if "error" in stats:
            return f"❌ Failed to get statistics for '{name}': {stats['error']}"

        response = f"📊 Knowledge base '{name}' statistics:\n"
        response += f"📄 Total documents: {stats['total_documents']}\n"
        response += f"📁 Total files: {stats['total_files']}\n"
        response += f"📂 Source paths: {', '.join(stats['source_paths'])}\n"
        response += f"🗂️ Vector database path: {stats['vector_db_path']}\n"
        response += f"📋 Supported extensions: {', '.join(stats['supported_extensions'])}\n"

        if stats.get("file_types"):
            response += f"📊 File types: {', '.join(f'{ext}({count})' for ext, count in stats['file_types'].items())}\n"

        response += f"🕒 Last updated: {stats['last_updated']}"

        return response
    except Exception as e:
        logger.error(f"Error getting statistics for '{name}': {e}")
        return f"❌ Error getting statistics for '{name}': {str(e)}"


@tool
def list_knowledge_bases() -> str:
    """List all created knowledge base instances"""
    global _knowledge_bases

    if not _knowledge_bases:
        return "📝 No knowledge bases created yet"

    response = f"📚 Available knowledge bases ({len(_knowledge_bases)}):\n\n"

    for name, kb in _knowledge_bases.items():
        stats = kb.get_stats()
        response += f"**{name}**\n"
        response += f"  📄 Documents: {stats.get('total_documents', 0)}\n"
        response += f"  📁 Files: {stats.get('total_files', 0)}\n"
        response += f"  📂 Sources: {', '.join(stats.get('source_paths', []))}\n"
        response += f"  🕒 Last updated: {stats.get('last_updated', 'Never')}\n\n"

    return response


@tool
def get_database_debug_info(name: str = "default") -> str:
    """Get database debugging information

    Args:
        name: Name of the knowledge base (default: "default")
    """
    try:
        kb = get_knowledge_base(name)
        info = kb.get_database_info()

        result = f"🔍 Database Debug Info for '{name}':\n\n"
        result += f"📊 Database Type: {info.get('type', 'Unknown')}\n"
        result += f"🗂️ Name: {info.get('name', 'Unknown')}\n"
        result += f"📁 Directory: {info.get('directory', 'Unknown')}\n"
        result += f"✅ Exists: {info.get('exists', False)}\n"
        result += f"📂 Directory Exists: {info.get('directory_exists', False)}\n"
        result += f"🔢 Collection Count: {info.get('collection_count', 'Unknown')}\n"
        result += f"🐛 Debug Mode: {info.get('debug_mode', False)}\n"
        result += f"🔌 Database Status: {'Exists' if info.get('database_exists', False) else 'Not Found'}\n"

        if info.get("db_stats_error"):
            result += f"⚠️ Error getting stats: {info['db_stats_error']}\n"

        return result
    except Exception as e:
        logger.error(f"Error getting debug info for '{name}': {e}")
        return f"❌ Error getting debug info for '{name}': {str(e)}"


@tool
def switch_database_backend(name: str = "default", db_type: str = "chroma", debug_mode: bool = False) -> str:
    """Switch database backend for a knowledge base

    Args:
        name: Name of the knowledge base (default: "default")
        db_type: Database type to switch to (e.g., "chroma")
        debug_mode: Enable debug mode
    """
    try:
        kb = get_knowledge_base(name)

        if kb.switch_database_backend(db_type, debug_mode):
            return f"✅ Successfully switched '{name}' to '{db_type}' backend with debug_mode={debug_mode}"
        else:
            return f"❌ Failed to switch '{name}' to '{db_type}' backend"
    except Exception as e:
        logger.error(f"Error switching database backend for '{name}': {e}")
        return f"❌ Error switching database backend for '{name}': {str(e)}"
