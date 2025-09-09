"""
Blog knowledge base tools
Convert blog content to vector database for AI retrieval
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
    """Blog knowledge base manager"""
    
    def __init__(self, blog_path: str, vector_db_path: str = "data/vector_db"):
        self.blog_path = Path(blog_path)
        self.vector_db_path = Path(vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model - use better Chinese model
        embedding_model = CONFIG.get("embedding_model", "BAAI/bge-large-zh-v1.5")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}  # Normalize embeddings during encoding
        )
        
        # Initialize text splitter - use parameters from configuration
        chunk_size = CONFIG.get("chunk_size", 512)
        chunk_overlap = CONFIG.get("chunk_overlap", 100)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]  # Add comma separator
        )
        
        # Initialize vector database
        self.vectorstore = None
        self._load_vectorstore()
        
        # Metadata file path
        self.metadata_file = self.vector_db_path / "metadata.json"
        self._load_metadata()
    
    def _load_vectorstore(self):
        """Load vector database"""
        try:
            if (self.vector_db_path / "chroma.sqlite3").exists():
                self.vectorstore = Chroma(
                    persist_directory=str(self.vector_db_path),
                    embedding_function=self.embeddings
                )
                logger.info("Vector database loaded successfully")
            else:
                logger.info("Vector database does not exist, will create new database")
        except Exception as e:
            logger.error(f"Failed to load vector database: {e}")
            self.vectorstore = None
    
    def _load_metadata(self):
        """Load metadata"""
        self.metadata = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                self.metadata = {}
    
    def _save_metadata(self):
        """Save metadata"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate file hash"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate file hash {file_path}: {e}")
            return ""
    
    def _parse_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse front matter
            front_matter = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        front_matter = yaml.safe_load(parts[1]) or {}
                        content = parts[2].strip()
                    except yaml.YAMLError:
                        pass
            
            # Convert Markdown to HTML
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
            logger.error(f"Failed to parse Markdown file {file_path}: {e}")
            return {'content': '', 'html_content': '', 'front_matter': {}, 'title': file_path.stem}
    
    def _should_update_file(self, file_path: Path) -> bool:
        """Check if file needs to be updated"""
        file_hash = self._get_file_hash(file_path)
        relative_path = str(file_path.relative_to(self.blog_path))
        
        if relative_path not in self.metadata:
            return True
        
        stored_hash = self.metadata[relative_path].get('hash', '')
        return file_hash != stored_hash
    
    def update_knowledge_base(self) -> Dict[str, Any]:
        """Update knowledge base"""
        if not self.blog_path.exists():
            return {"success": False, "message": f"Blog path does not exist: {self.blog_path}"}
        
        logger.info(f"Starting knowledge base update, blog path: {self.blog_path}")
        
        # Scan all Markdown files
        markdown_files = list(self.blog_path.rglob("*.md"))
        logger.info(f"Found {len(markdown_files)} Markdown files")
        
        updated_files = []
        new_documents = []
        
        for file_path in markdown_files:
            if self._should_update_file(file_path):
                logger.info(f"Processing file: {file_path}")
                
                # Parse file
                parsed_content = self._parse_markdown_file(file_path)
                
                # Split text
                chunks = self.text_splitter.split_text(parsed_content['content'])
                
                # Create document objects
                for i, chunk in enumerate(chunks):
                    try:
                        # Process metadata, convert lists to strings, ensure all values are basic types
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
                        
                        # Ensure all metadata values are types supported by ChromaDB
                        filtered_metadata = {}
                        for key, value in metadata.items():
                            if value is None:
                                continue
                            elif isinstance(value, (str, int, float, bool)):
                                filtered_metadata[key] = value
                            else:
                                filtered_metadata[key] = str(value)
                        
                        # Enhanced page content: add title, tags, category information to content beginning to improve search relevance
                        enhanced_content = f"Title: {parsed_content['title']}\n"
                        if parsed_content['tags']:
                            enhanced_content += f"Tags: {', '.join(str(tag) for tag in parsed_content['tags'])}\n"
                        if parsed_content['categories']:
                            enhanced_content += f"Categories: {', '.join(str(cat) for cat in parsed_content['categories'])}\n"
                        enhanced_content += f"\n{chunk}"
                        
                        doc = Document(
                            page_content=enhanced_content,
                            metadata=filtered_metadata
                        )
                        new_documents.append(doc)
                        
                    except Exception as e:
                        logger.error(f"Failed to create document {file_path} chunk {i}: {e}")
                        continue
                
                # Update metadata
                relative_path = str(file_path.relative_to(self.blog_path))
                self.metadata[relative_path] = {
                    'hash': self._get_file_hash(file_path),
                    'last_updated': datetime.now().isoformat(),
                    'title': parsed_content['title'],
                    'chunks_count': len(chunks)
                }
                
                updated_files.append(relative_path)
        
        if new_documents:
            # Create or update vector database
            if self.vectorstore is None:
                self.vectorstore = Chroma.from_documents(
                    documents=new_documents,
                    embedding=self.embeddings,
                    persist_directory=str(self.vector_db_path)
                )
            else:
                # Delete old documents and add new documents
                for file_path in updated_files:
                    try:
                        # Delete all chunks of this file
                        collection = self.vectorstore._collection
                        collection.delete(where={"source": file_path})
                        logger.info(f"Deleted old document: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old document {file_path}: {e}")
                
                # Add new documents
                self.vectorstore.add_documents(new_documents)
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"Knowledge base update completed, processed {len(updated_files)} files, created {len(new_documents)} document chunks")
        
        return {
            "success": True,
            "message": f"Knowledge base update completed",
            "updated_files": updated_files,
            "new_documents_count": len(new_documents),
            "total_files_processed": len(markdown_files)
        }
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base"""
        if self.vectorstore is None:
            return []
        
        try:
            # Use larger k value for initial search
            search_k = CONFIG.get("search_k", 10)
            initial_k = max(k * 2, search_k)
            
            # Perform similarity search
            docs = self.vectorstore.similarity_search_with_score(query, k=initial_k)
            
            results = []
            for doc, score in docs:
                # Calculate comprehensive score
                final_score = self._calculate_relevance_score(query, doc, score)
                
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': float(score),
                    'relevance_score': final_score
                })
            
            # Re-sort by relevance score
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Return top k results
            return results[:k]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _calculate_relevance_score(self, query: str, doc, vector_score: float) -> float:
        """Calculate document relevance score"""
        try:
            content = doc.page_content.lower()
            query_lower = query.lower()
            metadata = doc.metadata
            
            # Base vector similarity score (smaller distance is better, convert to score)
            base_score = 1.0 / (1.0 + vector_score)
            
            # Keyword matching score
            keyword_score = 0.0
            query_words = query_lower.split()
            for word in query_words:
                if word in content:
                    keyword_score += 1.0
            keyword_score = keyword_score / len(query_words) if query_words else 0.0
            
            # Title matching score
            title_score = 0.0
            title = metadata.get('title', '').lower()
            if title and query_lower in title:
                title_score = 2.0  # Give higher weight to title matching
            elif title:
                for word in query_words:
                    if word in title:
                        title_score += 0.5
            
            # Tag matching score
            tags_score = 0.0
            tags = metadata.get('tags', '').lower()
            if tags and query_lower in tags:
                tags_score = 1.5
            elif tags:
                for word in query_words:
                    if word in tags:
                        tags_score += 0.3
            
            # Category matching score
            category_score = 0.0
            categories = metadata.get('categories', '').lower()
            if categories and query_lower in categories:
                category_score = 1.0
            elif categories:
                for word in query_words:
                    if word in categories:
                        category_score += 0.2
            
            # Comprehensive score
            final_score = (
                base_score * 0.4 +           # Vector similarity 40%
                keyword_score * 0.3 +        # Keyword matching 30%
                title_score * 0.15 +         # Title matching 15%
                tags_score * 0.1 +           # Tag matching 10%
                category_score * 0.05        # Category matching 5%
            )
            
            return final_score
            
        except Exception as e:
            logger.error(f"Failed to calculate relevance score: {e}")
            return 1.0 / (1.0 + vector_score)  # fallback to base score
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        if self.vectorstore is None:
            return {"total_documents": 0, "total_files": 0}
        
        try:
            # Get collection information
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
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}


# Global knowledge base instance
_knowledge_base = None

def get_knowledge_base() -> BlogKnowledgeBase:
    """Get knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        blog_path = CONFIG.get("blog_path", "/home/zengls/repo/zeroDtree.github.io/content")
        vector_db_path = CONFIG.get("vector_db_path", "data/vector_db")
        _knowledge_base = BlogKnowledgeBase(blog_path, vector_db_path)
    return _knowledge_base


@tool
def update_blog_knowledge_base() -> str:
    """Update blog knowledge base, convert blog content to vector database for AI retrieval"""
    try:
        kb = get_knowledge_base()
        result = kb.update_knowledge_base()
        
        if result["success"]:
            return f"✅ Knowledge base update successful!\n" \
                   f"📁 Files processed: {result['total_files_processed']}\n" \
                   f"🔄 Files updated: {len(result['updated_files'])}\n" \
                   f"📄 New document chunks: {result['new_documents_count']}\n" \
                   f"📝 Updated files: {', '.join(result['updated_files'][:5])}" + \
                   (f" and {len(result['updated_files'])} more files" if len(result['updated_files']) > 5 else "")
        else:
            return f"❌ Knowledge base update failed: {result['message']}"
    except Exception as e:
        logger.error(f"Error updating knowledge base: {e}")
        return f"❌ Error updating knowledge base: {str(e)}"


@tool
def search_blog_knowledge_base(query: str, limit: int = 3) -> str:
    """Search for relevant content in blog knowledge base
    
    Args:
        query: Search query
        limit: Limit on number of results returned, default 5
    """
    try:
        kb = get_knowledge_base()
        results = kb.search(query, k=limit)
        
        if not results:
            return f"🔍 No content related to '{query}' found"
        
        response = f"🔍 Found {len(results)} relevant results:\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            preview_content = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
            content = result['content']
            score = result['score']
            relevance_score = result.get('relevance_score', score)
            
            response += f"**{i}. {metadata.get('title', 'No title')}**\n"
            response += f"📁 File: {metadata.get('source', 'Unknown')}\n"
            response += f"📅 Date: {metadata.get('date', 'Unknown')}\n"
            
            # Handle tag display
            tags = metadata.get('tags', '')
            if tags:
                response += f"🏷️ Tags: {tags}\n"
            
            # Handle category display
            categories = metadata.get('categories', '')
            if categories:
                response += f"📂 Categories: {categories}\n"
            
            response += f"📊 Vector similarity: {score:.3f}\n"
            response += f"🎯 Comprehensive relevance: {relevance_score:.3f}\n"
            response += f"📄 Content:\n{content}\n\n"
            response += "---\n\n"
        
        return response
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return f"❌ Error during search: {str(e)}"


@tool
def get_blog_knowledge_base_stats() -> str:
    """Get blog knowledge base statistics"""
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()
        
        if "error" in stats:
            return f"❌ Failed to get statistics: {stats['error']}"
        
        return f"📊 Blog knowledge base statistics:\n" \
               f"📄 Total documents: {stats['total_documents']}\n" \
               f"📁 Total files: {stats['total_files']}\n" \
               f"🗂️ Vector database path: {stats['vector_db_path']}\n" \
               f"📂 Blog path: {stats['blog_path']}\n" \
               f"🕒 Last updated: {stats['last_updated']}"
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return f"❌ Error getting statistics: {str(e)}"
