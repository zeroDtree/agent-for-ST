#!/usr/bin/env python3
"""
Generic embedding knowledge base management script
Provides command line interface to manage knowledge bases from any directory
Default source path: current directory
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from tools.embedding_knowledge_base import FilterOrder, get_knowledge_base

# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def _parse_patterns(patterns_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated pattern string into list"""
    if not patterns_str:
        return None
    return [pattern.strip() for pattern in patterns_str.split(",")]


def _parse_filter_order(filter_order: str) -> FilterOrder:
    """Convert string filter order to FilterOrder enum"""
    return FilterOrder.EXCLUDE_FIRST if filter_order.lower() == "exclude_first" else FilterOrder.INCLUDE_FIRST


def search_knowledge_base(query: str, name: str = "default", limit: int = 5) -> int:
    """Search knowledge base"""
    print(f"🔍 Search: {query} in '{name}'")
    kb = get_knowledge_base(name=name)
    results = kb.search(query, k=limit)

    if not results:
        print("❌ No relevant content found")
        return 1

    print(f"✅ Found {len(results)} relevant results:\n")

    for i, result in enumerate(results, 1):
        metadata = result["metadata"]
        preview_content = result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"]
        content = result["content"]
        score = result["score"]
        relevance_score = result.get("relevance_score", score)

        print(f"**{i}. {metadata.get('title', 'No title')}**")
        print(f"📁 File: {metadata.get('source', 'Unknown')}")
        print(f"📅 Date: {metadata.get('date', 'Unknown')}")

        # Handle tag display
        tags = metadata.get("tags", "")
        if tags:
            print(f"🏷️ Tags: {tags}")

        # Handle category display
        categories = metadata.get("categories", "")
        if categories:
            print(f"📂 Categories: {categories}")

        print(f"📊 Vector similarity: {score:.3f}")
        print(f"🎯 Comprehensive relevance: {relevance_score:.3f}")
        # print(f"📄 Content preview:\n{preview_content}")
        print(f"📄 Content:\n{content}")
        print("-" * 50)

    return 0


def show_stats(name: str = "default") -> int:
    """Show knowledge base statistics"""
    print(f"📊 Knowledge base '{name}' statistics:")
    kb = get_knowledge_base(name=name)
    stats = kb.get_stats()

    if "error" in stats:
        print(f"❌ Failed to get statistics: {stats['error']}")
        return 1

    print(f"📄 Total documents: {stats['total_documents']}")
    print(f"📁 Total files: {stats['total_files']}")
    print(f"📂 Source paths: {', '.join(stats['source_paths'])}")
    print(f"🗂️ Vector database path: {stats['vector_db_path']}")
    print(f"📋 Supported extensions: {', '.join(stats['supported_extensions'])}")

    if stats.get("file_types"):
        print(f"📊 File types: {', '.join(f'{ext}({count})' for ext, count in stats['file_types'].items())}")

    print(f"🕒 Last updated: {stats['last_updated']}")

    return 0


def list_knowledge_bases() -> int:
    """List all knowledge bases"""
    from pathlib import Path

    from config.config import CONFIG
    from tools.embedding_knowledge_base import get_knowledge_base

    # Scan for knowledge bases on disk
    vector_db_path = CONFIG.get("vector_db_path", "data/vector_db")
    vector_db_dir = Path(vector_db_path)

    discovered_kbs = {}

    # Then, scan disk for additional knowledge bases
    if vector_db_dir.exists():
        for kb_dir in vector_db_dir.iterdir():
            if kb_dir.is_dir():
                name = kb_dir.name
                config_file = kb_dir / "config.json"
                chroma_file = kb_dir / "chroma.sqlite3"

                # Check if this looks like a valid knowledge base
                if config_file.exists() or chroma_file.exists():
                    if name not in discovered_kbs:
                        # Load the knowledge base to get its stats
                        try:
                            kb = get_knowledge_base(name=name)
                            discovered_kbs[name] = kb
                        except Exception as e:
                            print(f"⚠️ Warning: Failed to load knowledge base '{name}': {e}")
                            import traceback

                            traceback.print_exc()
                            continue

    if not discovered_kbs:
        print("📝 No knowledge bases found")
        return 0

    print(f"📚 Available knowledge bases ({len(discovered_kbs)}):\n")

    for name, kb in discovered_kbs.items():
        try:
            stats = kb.get_stats()
            print(f"**{name}**")
            print(f"  📄 Documents: {stats.get('total_documents', 0)}")
            print(f"  📁 Files: {stats.get('total_files', 0)}")
            print(f"  📂 Sources: {', '.join(stats.get('source_paths', []))}")
            print(f"  🕒 Last updated: {stats.get('last_updated', 'Never')}\n")
        except Exception as e:
            print(f"**{name}** (Error loading stats: {e})")
            print(f"  ❌ Failed to get statistics\n")

    return 0


def create_or_update_knowledge_base(
    name: str = "default",
    source_paths: Optional[str] = None,
    file_patterns: Optional[str] = None,
    exclude_patterns: Optional[str] = None,
    include_patterns: Optional[str] = None,
    filter_order: Optional[str] = None,
    use_gitignore: Optional[bool] = None,
    description: str = "",
) -> int:
    """Create or update knowledge base (unified command)"""
    print(f"🔄 Processing knowledge base '{name}'...")

    try:
        pass

        # Parse parameters (only if provided)
        paths = _parse_patterns(source_paths) if source_paths else None
        excludes = _parse_patterns(exclude_patterns) if exclude_patterns else None
        includes = _parse_patterns(include_patterns) if include_patterns else None
        order = _parse_filter_order(filter_order) if filter_order else None

        # Get knowledge base - will automatically detect config changes and recreate if needed
        # Prepare kwargs, only include non-None values
        kwargs = {"name": name}
        if paths is not None:
            kwargs["source_paths"] = paths
        else:
            kwargs["source_paths"] = None
        if excludes is not None:
            kwargs["exclude_patterns"] = excludes
        if includes is not None:
            kwargs["include_patterns"] = includes
        if order is not None:
            kwargs["filter_order"] = order
        if use_gitignore is not None:
            kwargs["use_gitignore"] = use_gitignore

        kb = get_knowledge_base(**kwargs)

        # Update with file patterns
        patterns = _parse_patterns(file_patterns)
        result = kb.update_knowledge_base(file_patterns=patterns)

        if result["success"]:
            print("✅ Knowledge base processing successful!")
            print(f"📁 Files processed: {result['total_files_processed']}")
            print(f"🔄 Files updated: {len(result['updated_files'])}")
            print(f"📄 New document chunks: {result['new_documents_count']}")
            if description:
                print(f"📝 Description: {description}")
            if result["updated_files"]:
                print("📝 Updated files:")
                for file in result["updated_files"]:
                    print(f"  - {file}")
        else:
            print(f"❌ Knowledge base processing failed: {result['message']}")
            return 1

        return 0
    except Exception as e:
        print(f"❌ Error processing knowledge base '{name}': {e}")
        return 1


def add_texts_to_knowledge_base(name: str, texts: str, titles: str = "", sources: str = "") -> int:
    """Add text content directly to knowledge base"""
    print(f"📝 Adding texts to knowledge base '{name}'...")

    try:
        kb = get_knowledge_base(name=name)

        text_list = [t.strip() for t in texts.split("|")]
        title_list = [t.strip() for t in titles.split("|")] if titles else []
        source_list = [s.strip() for s in sources.split("|")] if sources else []

        # Prepare metadata
        metadatas = []
        for i, text in enumerate(text_list):
            metadata = {}
            if i < len(title_list) and title_list[i]:
                metadata["title"] = title_list[i]
            if i < len(source_list) and source_list[i]:
                metadata["source"] = source_list[i]
            metadatas.append(metadata)

        result = kb.add_documents_from_texts(text_list, metadatas)

        if result["success"]:
            print(f"✅ Added {len(text_list)} text documents to knowledge base '{name}'!")
            print(f"📄 New document chunks: {result['new_documents_count']}")
            return 0
        else:
            print(f"❌ Failed to add texts to knowledge base '{name}': {result['message']}")
            return 1
    except Exception as e:
        print(f"❌ Error adding texts to knowledge base '{name}': {e}")
        return 1


def _setup_update_parser(subparsers) -> None:
    """Setup update command parser (unified create/update)"""
    update_parser = subparsers.add_parser("update", help="Create or update knowledge base")
    update_parser.add_argument("-n", "--name", default="default", help="Knowledge base name")
    update_parser.add_argument("-s", "--source-paths", help="Comma-separated list of source paths")
    update_parser.add_argument("-p", "--patterns", help="Comma-separated list of file patterns")
    update_parser.add_argument("-d", "--description", default="", help="Description of the knowledge base")
    update_parser.add_argument("-e", "--exclude", help="Comma-separated list of regex exclude patterns")
    update_parser.add_argument("-i", "--include", help="Comma-separated list of regex include patterns")
    update_parser.add_argument(
        "--filter-order",
        choices=["exclude_first", "include_first"],
        help="Order to apply filters",
    )
    update_parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore filtering")


def _setup_other_parsers(subparsers) -> None:
    """Setup search, add, stats, and list command parsers"""
    # Search command
    search_parser = subparsers.add_parser("search", help="Search knowledge base")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-n", "--name", default="default", help="Knowledge base name")
    search_parser.add_argument("-l", "--limit", type=int, default=5, help="Result count limit")

    # Add texts command
    add_parser = subparsers.add_parser("add", help="Add text content to knowledge base")
    add_parser.add_argument("name", help="Knowledge base name")
    add_parser.add_argument("texts", help="Pipe-separated list of text content")
    add_parser.add_argument("-t", "--titles", default="", help="Pipe-separated list of titles")
    add_parser.add_argument("-s", "--sources", default="", help="Pipe-separated list of source identifiers")

    # Statistics command
    stats_parser = subparsers.add_parser("status", help="Show statistics")
    stats_parser.add_argument("-n", "--name", default="default", help="Knowledge base name")

    # List command
    subparsers.add_parser("list", help="List all knowledge bases")


def main() -> int:
    """Main function"""
    parser = argparse.ArgumentParser(description="Generic embedding knowledge base management tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command parsers
    _setup_update_parser(subparsers)
    _setup_other_parsers(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "update":
            return create_or_update_knowledge_base(
                args.name,
                args.source_paths,
                args.patterns,
                args.exclude,
                args.include,
                args.filter_order,
                not args.no_gitignore,
                args.description,
            )
        elif args.command == "search":
            return search_knowledge_base(args.query, args.name, args.limit)
        elif args.command == "add":
            return add_texts_to_knowledge_base(args.name, args.texts, args.titles, args.sources)
        elif args.command == "status":
            return show_stats(args.name)
        elif args.command == "list":
            return list_knowledge_bases()
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
