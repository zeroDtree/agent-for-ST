"""
博客知识库工具
将博客内容转换为向量数据库，供AI检索使用
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from langchain_core.tools import tool
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores.utils import filter_complex_metadata
import markdown
import yaml

from config.config import CONFIG
from utils.logger import logger


class BlogKnowledgeBase:
    """博客知识库管理器"""
    
    def __init__(self, blog_path: str, vector_db_path: str = "data/vector_db"):
        self.blog_path = Path(blog_path)
        self.vector_db_path = Path(vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化嵌入模型 - 使用更好的中文模型
        embedding_model = CONFIG.get("embedding_model", "BAAI/bge-large-zh-v1.5")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}  # 在编码时标准化embeddings
        )
        
        # 初始化文本分割器 - 使用配置中的参数
        chunk_size = CONFIG.get("chunk_size", 512)
        chunk_overlap = CONFIG.get("chunk_overlap", 100)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]  # 添加逗号分隔符
        )
        
        # 初始化向量数据库
        self.vectorstore = None
        self._load_vectorstore()
        
        # 元数据文件路径
        self.metadata_file = self.vector_db_path / "metadata.json"
        self._load_metadata()
    
    def _load_vectorstore(self):
        """加载向量数据库"""
        try:
            if (self.vector_db_path / "chroma.sqlite3").exists():
                self.vectorstore = Chroma(
                    persist_directory=str(self.vector_db_path),
                    embedding_function=self.embeddings
                )
                logger.info("向量数据库加载成功")
            else:
                logger.info("向量数据库不存在，将创建新的数据库")
        except Exception as e:
            logger.error(f"加载向量数据库失败: {e}")
            self.vectorstore = None
    
    def _load_metadata(self):
        """加载元数据"""
        self.metadata = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")
                self.metadata = {}
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return ""
    
    def _parse_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """解析Markdown文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析front matter
            front_matter = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        front_matter = yaml.safe_load(parts[1]) or {}
                        content = parts[2].strip()
                    except yaml.YAMLError:
                        pass
            
            # 转换Markdown为HTML
            html_content = markdown.markdown(content, extensions=['codehilite', 'tables'])
            
            return {
                'content': content,
                'html_content': html_content,
                'front_matter': front_matter,
                'title': front_matter.get('title', file_path.stem),
                'date': front_matter.get('date', ''),
                'tags': front_matter.get('tags', []),
                'categories': front_matter.get('categories', [])
            }
        except Exception as e:
            logger.error(f"解析Markdown文件失败 {file_path}: {e}")
            return {'content': '', 'html_content': '', 'front_matter': {}, 'title': file_path.stem}
    
    def _should_update_file(self, file_path: Path) -> bool:
        """检查文件是否需要更新"""
        file_hash = self._get_file_hash(file_path)
        relative_path = str(file_path.relative_to(self.blog_path))
        
        if relative_path not in self.metadata:
            return True
        
        stored_hash = self.metadata[relative_path].get('hash', '')
        return file_hash != stored_hash
    
    def update_knowledge_base(self) -> Dict[str, Any]:
        """更新知识库"""
        if not self.blog_path.exists():
            return {"success": False, "message": f"博客路径不存在: {self.blog_path}"}
        
        logger.info(f"开始更新知识库，博客路径: {self.blog_path}")
        
        # 扫描所有Markdown文件
        markdown_files = list(self.blog_path.rglob("*.md"))
        logger.info(f"找到 {len(markdown_files)} 个Markdown文件")
        
        updated_files = []
        new_documents = []
        
        for file_path in markdown_files:
            if self._should_update_file(file_path):
                logger.info(f"处理文件: {file_path}")
                
                # 解析文件
                parsed_content = self._parse_markdown_file(file_path)
                
                # 分割文本
                chunks = self.text_splitter.split_text(parsed_content['content'])
                
                # 创建文档对象
                for i, chunk in enumerate(chunks):
                    try:
                        # 处理元数据，将列表转换为字符串，确保所有值都是基础类型
                        metadata = {
                            'source': str(file_path.relative_to(self.blog_path)),
                            'title': str(parsed_content['title']),
                            'date': str(parsed_content['date']),
                            'tags': ', '.join(str(tag) for tag in parsed_content['tags']) if parsed_content['tags'] else '',
                            'categories': ', '.join(str(cat) for cat in parsed_content['categories']) if parsed_content['categories'] else '',
                            'chunk_index': int(i),
                            'total_chunks': int(len(chunks)),
                            'file_path': str(file_path)
                        }
                        
                        # 确保所有元数据值都是ChromaDB支持的类型
                        filtered_metadata = {}
                        for key, value in metadata.items():
                            if value is None:
                                continue
                            elif isinstance(value, (str, int, float, bool)):
                                filtered_metadata[key] = value
                            else:
                                filtered_metadata[key] = str(value)
                        
                        # 增强页面内容：将标题、标签、分类信息添加到内容开头，提高搜索相关性
                        enhanced_content = f"标题: {parsed_content['title']}\n"
                        if parsed_content['tags']:
                            enhanced_content += f"标签: {', '.join(str(tag) for tag in parsed_content['tags'])}\n"
                        if parsed_content['categories']:
                            enhanced_content += f"分类: {', '.join(str(cat) for cat in parsed_content['categories'])}\n"
                        enhanced_content += f"\n{chunk}"
                        
                        doc = Document(
                            page_content=enhanced_content,
                            metadata=filtered_metadata
                        )
                        new_documents.append(doc)
                        
                    except Exception as e:
                        logger.error(f"创建文档失败 {file_path} chunk {i}: {e}")
                        continue
                
                # 更新元数据
                relative_path = str(file_path.relative_to(self.blog_path))
                self.metadata[relative_path] = {
                    'hash': self._get_file_hash(file_path),
                    'last_updated': datetime.now().isoformat(),
                    'title': parsed_content['title'],
                    'chunks_count': len(chunks)
                }
                
                updated_files.append(relative_path)
        
        if new_documents:
            # 创建或更新向量数据库
            if self.vectorstore is None:
                self.vectorstore = Chroma.from_documents(
                    documents=new_documents,
                    embedding=self.embeddings,
                    persist_directory=str(self.vector_db_path)
                )
            else:
                # 删除旧文档并添加新文档
                for file_path in updated_files:
                    try:
                        # 删除该文件的所有chunks
                        collection = self.vectorstore._collection
                        collection.delete(where={"source": file_path})
                        logger.info(f"删除旧文档: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除旧文档失败 {file_path}: {e}")
                
                # 添加新文档
                self.vectorstore.add_documents(new_documents)
            
            # 保存元数据
            self._save_metadata()
            
            logger.info(f"知识库更新完成，处理了 {len(updated_files)} 个文件，创建了 {len(new_documents)} 个文档块")
        
        return {
            "success": True,
            "message": f"知识库更新完成",
            "updated_files": updated_files,
            "new_documents_count": len(new_documents),
            "total_files_processed": len(markdown_files)
        }
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库"""
        if self.vectorstore is None:
            return []
        
        try:
            # 使用更大的k值进行初步搜索
            search_k = CONFIG.get("search_k", 10)
            initial_k = max(k * 2, search_k)
            
            # 执行相似性搜索
            docs = self.vectorstore.similarity_search_with_score(query, k=initial_k)
            
            results = []
            for doc, score in docs:
                # 计算综合评分
                final_score = self._calculate_relevance_score(query, doc, score)
                
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': float(score),
                    'relevance_score': final_score
                })
            
            # 按相关性得分重新排序
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # 返回前k个结果
            return results[:k]
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def _calculate_relevance_score(self, query: str, doc, vector_score: float) -> float:
        """计算文档相关性得分"""
        try:
            content = doc.page_content.lower()
            query_lower = query.lower()
            metadata = doc.metadata
            
            # 基础向量相似性得分（距离越小越好，转换为得分）
            base_score = 1.0 / (1.0 + vector_score)
            
            # 关键词匹配得分
            keyword_score = 0.0
            query_words = query_lower.split()
            for word in query_words:
                if word in content:
                    keyword_score += 1.0
            keyword_score = keyword_score / len(query_words) if query_words else 0.0
            
            # 标题匹配得分
            title_score = 0.0
            title = metadata.get('title', '').lower()
            if title and query_lower in title:
                title_score = 2.0  # 标题匹配给更高权重
            elif title:
                for word in query_words:
                    if word in title:
                        title_score += 0.5
            
            # 标签匹配得分
            tags_score = 0.0
            tags = metadata.get('tags', '').lower()
            if tags and query_lower in tags:
                tags_score = 1.5
            elif tags:
                for word in query_words:
                    if word in tags:
                        tags_score += 0.3
            
            # 分类匹配得分
            category_score = 0.0
            categories = metadata.get('categories', '').lower()
            if categories and query_lower in categories:
                category_score = 1.0
            elif categories:
                for word in query_words:
                    if word in categories:
                        category_score += 0.2
            
            # 综合得分
            final_score = (
                base_score * 0.4 +           # 向量相似性 40%
                keyword_score * 0.3 +        # 关键词匹配 30%
                title_score * 0.15 +         # 标题匹配 15%
                tags_score * 0.1 +           # 标签匹配 10%
                category_score * 0.05        # 分类匹配 5%
            )
            
            return final_score
            
        except Exception as e:
            logger.error(f"计算相关性得分失败: {e}")
            return 1.0 / (1.0 + vector_score)  # fallback到基础得分
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if self.vectorstore is None:
            return {"total_documents": 0, "total_files": 0}
        
        try:
            # 获取集合信息
            collection = self.vectorstore._collection
            total_docs = collection.count()
            
            return {
                "total_documents": total_docs,
                "total_files": len(self.metadata),
                "vector_db_path": str(self.vector_db_path),
                "blog_path": str(self.blog_path),
                "last_updated": max(
                    [meta.get('last_updated', '') for meta in self.metadata.values()],
                    default=''
                )
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}


# 全局知识库实例
_knowledge_base = None

def get_knowledge_base() -> BlogKnowledgeBase:
    """获取知识库实例"""
    global _knowledge_base
    if _knowledge_base is None:
        blog_path = CONFIG.get("blog_path", "/home/zengls/repo/zeroDtree.github.io/content")
        vector_db_path = CONFIG.get("vector_db_path", "data/vector_db")
        _knowledge_base = BlogKnowledgeBase(blog_path, vector_db_path)
    return _knowledge_base


@tool
def update_blog_knowledge_base() -> str:
    """更新博客知识库，将博客内容转换为向量数据库供AI检索使用"""
    try:
        kb = get_knowledge_base()
        result = kb.update_knowledge_base()
        
        if result["success"]:
            return f"✅ 知识库更新成功！\n" \
                   f"📁 处理文件数: {result['total_files_processed']}\n" \
                   f"🔄 更新文件数: {len(result['updated_files'])}\n" \
                   f"📄 新增文档块: {result['new_documents_count']}\n" \
                   f"📝 更新文件: {', '.join(result['updated_files'][:5])}" + \
                   (f" 等{len(result['updated_files'])}个文件" if len(result['updated_files']) > 5 else "")
        else:
            return f"❌ 知识库更新失败: {result['message']}"
    except Exception as e:
        logger.error(f"更新知识库时出错: {e}")
        return f"❌ 更新知识库时出错: {str(e)}"


@tool
def search_blog_knowledge_base(query: str, limit: int = 3) -> str:
    """在博客知识库中搜索相关内容
    
    Args:
        query: 搜索查询
        limit: 返回结果数量限制，默认5个
    """
    try:
        kb = get_knowledge_base()
        results = kb.search(query, k=limit)
        
        if not results:
            return f"🔍 未找到与 '{query}' 相关的内容"
        
        response = f"🔍 找到 {len(results)} 个相关结果:\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            preview_content = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
            content = result['content']
            score = result['score']
            relevance_score = result.get('relevance_score', score)
            
            response += f"**{i}. {metadata.get('title', '无标题')}**\n"
            response += f"📁 文件: {metadata.get('source', '未知')}\n"
            response += f"📅 日期: {metadata.get('date', '未知')}\n"
            
            # 处理标签显示
            tags = metadata.get('tags', '')
            if tags:
                response += f"🏷️ 标签: {tags}\n"
            
            # 处理分类显示
            categories = metadata.get('categories', '')
            if categories:
                response += f"📂 分类: {categories}\n"
            
            response += f"📊 向量相似度: {score:.3f}\n"
            response += f"🎯 综合相关性: {relevance_score:.3f}\n"
            response += f"📄 内容:\n{content}\n\n"
            response += "---\n\n"
        
        return response
    except Exception as e:
        logger.error(f"搜索知识库时出错: {e}")
        return f"❌ 搜索时出错: {str(e)}"


@tool
def get_blog_knowledge_base_stats() -> str:
    """获取博客知识库的统计信息"""
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()
        
        if "error" in stats:
            return f"❌ 获取统计信息失败: {stats['error']}"
        
        return f"📊 博客知识库统计信息:\n" \
               f"📄 总文档数: {stats['total_documents']}\n" \
               f"📁 总文件数: {stats['total_files']}\n" \
               f"🗂️ 向量数据库路径: {stats['vector_db_path']}\n" \
               f"📂 博客路径: {stats['blog_path']}\n" \
               f"🕒 最后更新: {stats['last_updated']}"
    except Exception as e:
        logger.error(f"获取统计信息时出错: {e}")
        return f"❌ 获取统计信息时出错: {str(e)}"
