"""
Chroma 服务 - 向量数据库存储和检索
参考 TradingAgents-CN 的实现
"""
import os
import json
from typing import Optional, List, Dict, Any
import chromadb

class ChromaService:
    """Chroma向量数据库服务类"""

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        self._client: Optional[chromadb.Client] = None
        self._collection_report: Optional[chromadb.Collection] = None
        self._collection_knowledge: Optional[chromadb.Collection] = None

    def connect(self) -> "ChromaService":
        """建立Chroma连接"""
        if self._client is None:
            # 确保目录存在
            os.makedirs(self.persist_directory, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.persist_directory
            )
            print(f"[Chroma] 已连接到 {self.persist_directory}")

        # 初始化集合
        self._init_collections()
        return self

    def _init_collections(self):
        """初始化集合"""
        try:
            self._collection_report = self._client.get_or_create_collection(
                name="report_chunks",
                metadata={"description": "研报文本分块向量存储"}
            )
            print("[Chroma] report_chunks 集合已就绪")
        except Exception as e:
            print(f"[Chroma] 获取report_chunks集合失败: {e}")

        try:
            self._collection_knowledge = self._client.get_or_create_collection(
                name="knowledge_chunks",
                metadata={"description": "知识库文本分块向量存储"}
            )
            print("[Chroma] knowledge_chunks 集合已就绪")
        except Exception as e:
            print(f"[Chroma] 获取knowledge_chunks集合失败: {e}")

    def disconnect(self):
        """断开Chroma连接"""
        if self._client:
            self._client.reset()
            self._client = None
            self._collection_report = None
            self._collection_knowledge = None
            print("[Chroma] 连接已关闭")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    # ========== 集合操作 ==========

    def get_collection(self, collection_name: str) -> Optional[Any]:
        """获取集合"""
        try:
            if collection_name == "report_chunks":
                return self._collection_report
            elif collection_name == "knowledge_chunks":
                return self._collection_knowledge
            return self._client.get_collection(collection_name)
        except Exception:
            return None

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            collections = self._client.list_collections()
            return [c.name for c in collections]
        except Exception:
            return []

    def reset_collection(self, collection_name: str) -> bool:
        """重置集合"""
        try:
            self._client.delete_collection(collection_name)
            self._init_collections()
            print(f"[Chroma] 集合 {collection_name} 已重置")
            return True
        except Exception as e:
            print(f"[Chroma] 重置集合失败: {e}")
            return False

    # ========== 向量操作 ==========

    def insert_vectors(self, collection_name: str, vectors: List[Dict]) -> List[str]:
        """
        插入向量数据

        Args:
            collection_name: 集合名称
            vectors: 向量数据列表，每项包含:
                - id: 唯一ID
                - text: 文本内容
                - embedding: 向量
                - report_id: 报告ID
                - page: 页码
                - chunk_index: 块索引
                - metadata: 元数据(dict)

        Returns:
            插入的ID列表
        """
        collection = self.get_collection(collection_name)
        if not collection:
            raise Exception(f"集合 {collection_name} 不存在")

        # 准备数据
        ids = []
        texts = []
        embeddings = []
        metadatas = []

        for v in vectors:
            ids.append(v["id"])
            texts.append(v["text"])
            embeddings.append(v["embedding"])

            # 构建元数据（只包含Chroma支持的简单类型）
            meta = {
                "report_id": str(v.get("report_id", "")),
                "page": int(v.get("page", 0)),
                "chunk_index": int(v.get("chunk_index", 0))
            }
            if v.get("metadata"):
                for k, val in v["metadata"].items():
                    # Chroma只支持str, int, float, bool类型
                    if isinstance(val, (str, int, float, bool)) and val:
                        meta[k] = val
                    elif isinstance(val, list) and len(val) > 0:
                        # 列表类型转成逗号分隔的字符串
                        meta[k] = ",".join(str(x) for x in val[:10])
            metadatas.append(meta)

        # 插入数据
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        print(f"[Chroma] 已插入 {len(ids)} 条向量到 {collection_name}")
        return ids

    def search_vectors(self, collection_name: str, query_vector: List[float],
                      top_k: int = 5, report_id: str = None) -> List[Dict]:
        """
        搜索相似向量

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回数量
            report_id: 可选，限定报告ID

        Returns:
            搜索结果列表
        """
        collection = self.get_collection(collection_name)
        if not collection:
            raise Exception(f"集合 {collection_name} 不存在")

        # 构建查询条件
        where_filter = None
        if report_id:
            where_filter = {"report_id": report_id}

        try:
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # 整理结果
            search_results = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    search_results.append({
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "report_id": metadata.get("report_id", ""),
                        "page": metadata.get("page", 0),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "metadata": metadata,
                        "score": 1 - results["distances"][0][i] if results["distances"] else 0
                    })

            return search_results

        except Exception as e:
            print(f"[Chroma] 搜索失败: {e}")
            return []

    def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """删除向量"""
        collection = self.get_collection(collection_name)
        if not collection:
            return False

        try:
            collection.delete(ids=ids)
            print(f"[Chroma] 已从 {collection_name} 删除 {len(ids)} 条向量")
            return True
        except Exception as e:
            print(f"[Chroma] 删除向量失败: {e}")
            return False

    def delete_by_report_id(self, collection_name: str, report_id: str) -> bool:
        """删除指定报告的所有向量"""
        collection = self.get_collection(collection_name)
        if not collection:
            return False

        try:
            collection.delete(where={"report_id": report_id})
            print(f"[Chroma] 已从 {collection_name} 删除报告 {report_id} 的所有向量")
            return True
        except Exception as e:
            print(f"[Chroma] 删除向量失败: {e}")
            return False

    def get_collection_stats(self, collection_name: str) -> Dict:
        """获取集合统计信息"""
        collection = self.get_collection(collection_name)
        if not collection:
            return {"exists": False}

        try:
            count = collection.count()
            return {
                "exists": True,
                "name": collection_name,
                "entities": count
            }
        except Exception:
            return {"exists": True, "name": collection_name, "entities": 0}

    # ========== 便利方法 ==========

    def init_default_collections(self):
        """初始化默认集合"""
        self._init_collections()
        print("[Chroma] 默认集合初始化完成")


# 单例模式全局实例
_chroma_service: Optional[ChromaService] = None

def get_chroma_service() -> ChromaService:
    """获取Chroma服务单例"""
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaService().connect()
    return _chroma_service
