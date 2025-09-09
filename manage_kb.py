#!/usr/bin/env python3
"""
Blog knowledge base management script
Provides command line interface to manage blog knowledge base
"""

import argparse
import sys
from pathlib import Path

# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tools.knowledge_base import get_knowledge_base
from config.config import CONFIG


def update_knowledge_base():
    """Update knowledge base"""
    print("🔄 Starting blog knowledge base update...")
    kb = get_knowledge_base()
    result = kb.update_knowledge_base()
    
    if result["success"]:
        print("✅ Knowledge base update successful!")
        print(f"📁 Files processed: {result['total_files_processed']}")
        print(f"🔄 Files updated: {len(result['updated_files'])}")
        print(f"📄 New document chunks: {result['new_documents_count']}")
        if result['updated_files']:
            print("📝 Updated files:")
            for file in result['updated_files']:
                print(f"  - {file}")
    else:
        print(f"❌ Knowledge base update failed: {result['message']}")
        return 1
    
    return 0


def search_knowledge_base(query: str, limit: int = 5):
    """Search knowledge base"""
    print(f"🔍 Search: {query}")
    kb = get_knowledge_base()
    results = kb.search(query, k=limit)
    
    if not results:
        print("❌ No relevant content found")
        return 1
    
    print(f"✅ Found {len(results)} relevant results:\n")
    
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        preview_content = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
        content = result['content']
        score = result['score']
        relevance_score = result.get('relevance_score', score)
        
        print(f"**{i}. {metadata.get('title', 'No title')}**")
        print(f"📁 File: {metadata.get('source', 'Unknown')}")
        print(f"📅 Date: {metadata.get('date', 'Unknown')}")
        
        # Handle tag display
        tags = metadata.get('tags', '')
        if tags:
            print(f"🏷️ Tags: {tags}")
        
        # Handle category display
        categories = metadata.get('categories', '')
        if categories:
            print(f"📂 Categories: {categories}")
        
        print(f"📊 Vector similarity: {score:.3f}")
        print(f"🎯 Comprehensive relevance: {relevance_score:.3f}")
        # print(f"📄 Content preview:\n{preview_content}")
        print(f"📄 Content:\n{content}")
        print("-" * 50)
    
    return 0


def show_stats():
    """Show knowledge base statistics"""
    print("📊 Blog knowledge base statistics:")
    kb = get_knowledge_base()
    stats = kb.get_stats()
    
    if "error" in stats:
        print(f"❌ Failed to get statistics: {stats['error']}")
        return 1
    
    print(f"📄 Total documents: {stats['total_documents']}")
    print(f"📁 Total files: {stats['total_files']}")
    print(f"🗂️ Vector database path: {stats['vector_db_path']}")
    print(f"📂 Blog path: {stats['blog_path']}")
    print(f"🕒 Last updated: {stats['last_updated']}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="Blog knowledge base management tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update knowledge base')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-l', '--limit', type=int, default=5, help='Result count limit')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'update':
            return update_knowledge_base()
        elif args.command == 'search':
            return search_knowledge_base(args.query, args.limit)
        elif args.command == 'stats':
            return show_stats()
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
