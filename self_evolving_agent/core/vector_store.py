"""
向量数据库模块 — 基于内存的轻量级向量存储 + 硅基流动Embedding

功能:
1. 文本向量化（通过硅基流动Embedding API）
2. 向量存储与检索（余弦相似度）
3. RAG检索增强生成
4. 知识库管理

支持模型:
- BAAI/bge-m3 (推荐，多语言)
- BAAI/bge-large-zh-v1.5
- Qwen/Qwen3-Embedding-0.6B
"""

import os
import json
import time
import threading
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# 使用标准库实现，不增加额外依赖
try:
    import urllib.request
    import urllib.error
    HAS_URLIB = True
except ImportError:
    HAS_URLIB = False


@dataclass
class Document:
    """文档"""
    doc_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    """搜索结果"""
    doc: Document
    score: float


class EmbeddingClient:
    """
    硅基流动Embedding客户端
    """

    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "BAAI/bge-m3"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ):
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY", "")
        self.base_url = (base_url or os.environ.get("SILICONFLOW_BASE_URL", "")).rstrip("/") or self.DEFAULT_BASE_URL
        self.model = model or os.environ.get("SILICONFLOW_EMBEDDING_MODEL", "") or self.DEFAULT_MODEL
        self.timeout = timeout
        self._stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "total_latency_ms": 0,
        }
        self._lock = threading.Lock()

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        将文本列表转换为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        if not HAS_URLIB:
            return [[] for _ in texts]

        start_time = time.time()

        # 构建请求体
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            latency_ms = (time.time() - start_time) * 1000

            # 解析响应
            embeddings = []
            for item in sorted(data.get("data", []), key=lambda x: x.get("index", 0)):
                embeddings.append(item.get("embedding", []))

            with self._lock:
                self._stats["requests_total"] += 1
                self._stats["requests_success"] += 1
                self._stats["total_latency_ms"] += latency_ms

            return embeddings

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            with self._lock:
                self._stats["requests_total"] += 1
                self._stats["requests_failed"] += 1
            print(f"[Embedding] Error: {e}")
            return [[] for _ in texts]

    def embed_single(self, text: str) -> List[float]:
        """嵌入单个文本"""
        results = self.embed([text])
        return results[0] if results else []

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            stats = dict(self._stats)
            if stats["requests_total"] > 0:
                stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["requests_total"]
                stats["success_rate"] = stats["requests_success"] / stats["requests_total"]
            return stats


class VectorStore:
    """
    轻量级内存向量数据库
    
    特性:
    - 基于余弦相似度的最近邻搜索
    - 自动向量化（通过Embedding API）
    - 线程安全
    - 支持元数据过滤
    """

    def __init__(self, store_id: str = "default", embedding_client: Optional[EmbeddingClient] = None):
        self.store_id = store_id
        self._embedding = embedding_client or EmbeddingClient()
        self._documents: Dict[str, Document] = {}
        self._lock = threading.RLock()

    # ============================================================
    # 文档管理
    # ============================================================

    def add_document(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        添加文档（自动向量化）
        """
        embedding = self._embedding.embed_single(content)
        if not embedding:
            return False

        with self._lock:
            self._documents[doc_id] = Document(
                doc_id=doc_id,
                content=content,
                embedding=embedding,
                metadata=metadata or {},
            )
        return True

    def add_documents(self, documents: List[Tuple[str, str, Optional[Dict[str, Any]]]]) -> int:
        """
        批量添加文档
        
        Args:
            documents: [(doc_id, content, metadata), ...]
        """
        if not documents:
            return 0

        # 批量获取向量
        texts = [doc[1] for doc in documents]
        embeddings = self._embedding.embed(texts)

        success_count = 0
        with self._lock:
            for i, (doc_id, content, metadata) in enumerate(documents):
                if i < len(embeddings) and embeddings[i]:
                    self._documents[doc_id] = Document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embeddings[i],
                        metadata=metadata or {},
                    )
                    success_count += 1

        return success_count

    def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档"""
        with self._lock:
            return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                return True
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """列出所有文档（不含向量）"""
        with self._lock:
            return [
                {
                    "doc_id": d.doc_id,
                    "content": d.content[:200] + "..." if len(d.content) > 200 else d.content,
                    "metadata": d.metadata,
                    "timestamp": d.timestamp,
                }
                for d in self._documents.values()
            ]

    def clear(self) -> None:
        """清空所有文档"""
        with self._lock:
            self._documents.clear()

    # ============================================================
    # 向量搜索
    # ============================================================

    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        向量相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件
            
        Returns:
            搜索结果列表（按相似度降序）
        """
        query_embedding = self._embedding.embed_single(query)
        if not query_embedding:
            return []

        with self._lock:
            results = []
            for doc in self._documents.values():
                # 元数据过滤
                if filter_metadata and not self._match_metadata(doc.metadata, filter_metadata):
                    continue

                if doc.embedding:
                    score = self._cosine_similarity(query_embedding, doc.embedding)
                    results.append(SearchResult(doc=doc, score=score))

            # 按相似度降序排序
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]

    def search_similar(self, doc_id: str, top_k: int = 5) -> List[SearchResult]:
        """
        查找与指定文档相似的文档
        """
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc or not doc.embedding:
                return []

            results = []
            for other in self._documents.values():
                if other.doc_id != doc_id and other.embedding:
                    score = self._cosine_similarity(doc.embedding, other.embedding)
                    results.append(SearchResult(doc=other, score=score))

            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]

    # ============================================================
    # RAG检索增强
    # ============================================================

    def retrieve_for_rag(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        为RAG检索相关文档片段
        
        Returns:
            文档片段列表，每个包含content和score
        """
        results = self.search(query, top_k=top_k)
        return [
            {
                "content": r.doc.content,
                "score": r.score,
                "doc_id": r.doc.doc_id,
                "metadata": r.doc.metadata,
            }
            for r in results
        ]

    # ============================================================
    # 工具方法
    # ============================================================

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if len(a) != len(b) or not a:
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def _match_metadata(doc_meta: Dict[str, Any], filter_meta: Dict[str, Any]) -> bool:
        """检查文档元数据是否匹配过滤条件"""
        for key, value in filter_meta.items():
            if key not in doc_meta or doc_meta[key] != value:
                return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        with self._lock:
            return {
                "store_id": self.store_id,
                "document_count": len(self._documents),
                "embedding_stats": self._embedding.get_stats(),
            }


class RAGService:
    """
    RAG检索增强生成服务
    
    整合向量数据库 + LLM，实现知识库问答
    """

    def __init__(self, vector_store: Optional[VectorStore] = None, llm_service=None):
        self.vector_store = vector_store or VectorStore()
        self.llm = llm_service

    def add_knowledge(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加知识到知识库"""
        return self.vector_store.add_document(doc_id, content, metadata)

    def add_knowledges(self, documents: List[Tuple[str, str, Optional[Dict[str, Any]]]]) -> int:
        """批量添加知识"""
        return self.vector_store.add_documents(documents)

    def query(self, question: str, top_k: int = 3, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        RAG问答
        
        流程:
        1. 向量检索相关文档
        2. 构建上下文提示
        3. 调用LLM生成答案
        """
        # 1. 检索相关文档
        retrieved = self.vector_store.retrieve_for_rag(question, top_k=top_k)

        if not retrieved:
            return {
                "answer": "知识库中没有找到相关内容。",
                "sources": [],
                "context_used": False,
            }

        # 2. 构建上下文
        context_parts = []
        for i, doc in enumerate(retrieved, 1):
            context_parts.append(f"[文档{i}] {doc['content']}")

        context = "\n\n".join(context_parts)

        # 3. 构建提示
        prompt = f"""基于以下参考文档回答问题。如果文档中没有答案，请明确说明。

参考文档:
{context}

问题: {question}

请根据参考文档给出准确、简洁的回答:"""

        # 4. 调用LLM
        if self.llm:
            answer = self.llm.quick_chat(prompt, system_prompt or "你是一个基于知识库的智能问答助手。")
        else:
            answer = "[LLM服务未配置]"

        return {
            "answer": answer,
            "sources": retrieved,
            "context_used": True,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取RAG服务统计"""
        return self.vector_store.get_stats()


# ============================================================================
# 快速创建
# ============================================================================

def create_vector_store(store_id: str = "default") -> VectorStore:
    """创建向量存储"""
    return VectorStore(store_id=store_id)


def create_rag_service(vector_store: Optional[VectorStore] = None, llm_service=None) -> RAGService:
    """创建RAG服务"""
    return RAGService(vector_store=vector_store, llm_service=llm_service)
