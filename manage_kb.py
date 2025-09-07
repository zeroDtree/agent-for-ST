#!/usr/bin/env python3
"""
博客知识库管理脚本
提供命令行接口来管理博客知识库
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from tools.knowledge_base import get_knowledge_base
from config.config import CONFIG


def update_knowledge_base():
    """更新知识库"""
    print("🔄 开始更新博客知识库...")
    kb = get_knowledge_base()
    result = kb.update_knowledge_base()
    
    if result["success"]:
        print("✅ 知识库更新成功！")
        print(f"📁 处理文件数: {result['total_files_processed']}")
        print(f"🔄 更新文件数: {len(result['updated_files'])}")
        print(f"📄 新增文档块: {result['new_documents_count']}")
        if result['updated_files']:
            print("📝 更新的文件:")
            for file in result['updated_files']:
                print(f"  - {file}")
    else:
        print(f"❌ 知识库更新失败: {result['message']}")
        return 1
    
    return 0


def search_knowledge_base(query: str, limit: int = 5):
    """搜索知识库"""
    print(f"🔍 搜索: {query}")
    kb = get_knowledge_base()
    results = kb.search(query, k=limit)
    
    if not results:
        print("❌ 未找到相关内容")
        return 1
    
    print(f"✅ 找到 {len(results)} 个相关结果:\n")
    
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        preview_content = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
        content = result['content']
        score = result['score']
        relevance_score = result.get('relevance_score', score)
        
        print(f"**{i}. {metadata.get('title', '无标题')}**")
        print(f"📁 文件: {metadata.get('source', '未知')}")
        print(f"📅 日期: {metadata.get('date', '未知')}")
        
        # 处理标签显示
        tags = metadata.get('tags', '')
        if tags:
            print(f"🏷️ 标签: {tags}")
        
        # 处理分类显示
        categories = metadata.get('categories', '')
        if categories:
            print(f"📂 分类: {categories}")
        
        print(f"📊 向量相似度: {score:.3f}")
        print(f"🎯 综合相关性: {relevance_score:.3f}")
        # print(f"📄 内容预览:\n{preview_content}")
        print(f"📄 内容:\n{content}")
        print("-" * 50)
    
    return 0


def show_stats():
    """显示知识库统计信息"""
    print("📊 博客知识库统计信息:")
    kb = get_knowledge_base()
    stats = kb.get_stats()
    
    if "error" in stats:
        print(f"❌ 获取统计信息失败: {stats['error']}")
        return 1
    
    print(f"📄 总文档数: {stats['total_documents']}")
    print(f"📁 总文件数: {stats['total_files']}")
    print(f"🗂️ 向量数据库路径: {stats['vector_db_path']}")
    print(f"📂 博客路径: {stats['blog_path']}")
    print(f"🕒 最后更新: {stats['last_updated']}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="博客知识库管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 更新命令
    update_parser = subparsers.add_parser('update', help='更新知识库')
    
    # 搜索命令
    search_parser = subparsers.add_parser('search', help='搜索知识库')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('-l', '--limit', type=int, default=5, help='结果数量限制')
    
    # 统计命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    
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
        print("\n👋 操作已取消")
        return 1
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
