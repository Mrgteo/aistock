"""
Embedding 服务 - 文本向量化（使用阿里云DashScope text-embedding-v4）
"""
import os
import hashlib
from typing import Optional, List
import requests
from backend.services.redis_service import get_redis_service

class EmbeddingService:
    """文本向量化服务（阿里云DashScope）"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model or os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
        self.dimension = 1024  # text-embedding-v4 输出维度为1024
        self._redis = None

    def _get_redis(self):
        """获取Redis缓存"""
        if self._redis is None:
            try:
                self._redis = get_redis_service()
            except Exception:
                self._redis = None
        return self._redis

    def _text_hash(self, text: str) -> str:
        """计算文本哈希用于缓存"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def embed_text(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """
        单文本嵌入

        Args:
            text: 文本内容
            use_cache: 是否使用缓存

        Returns:
            向量列表
        """
        if not text or not text.strip():
            return None

        # 检查缓存
        if use_cache:
            redis = self._get_redis()
            if redis:
                cached = redis.get_cached_embedding(self._text_hash(text))
                if cached:
                    return cached

        try:
            response = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": {"texts": [text[:8192]]}
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"[Embedding] API error: {response.status_code}, {response.text}")
                return None

            result = response.json()
            # DashScope返回格式: {"output": {"embeddings": [{"embedding": [...], "text_index": 0}]}}
            embedding = result["output"]["embeddings"][0]["embedding"]

            # 写入缓存
            if use_cache and self._redis:
                self._redis.cache_embedding(self._text_hash(text), embedding)

            return embedding

        except Exception as e:
            print(f"[Embedding] 向量化失败: {e}")
            return None

    def embed_batch(self, texts: List[str], use_cache: bool = True) -> List[Optional[List[float]]]:
        """
        批量文本嵌入

        Args:
            texts: 文本列表
            use_cache: 是否使用缓存

        Returns:
            向量列表
        """
        if not texts:
            return []

        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []

        redis = self._get_redis() if use_cache else None

        # 过滤空文本并检查缓存
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = None
                continue

            if use_cache and redis:
                cached = redis.get_cached_embedding(self._text_hash(text))
                if cached:
                    results[i] = cached
                    continue

            texts_to_embed.append(text[:8192])
            indices_to_embed.append(i)

        # 批量API调用
        if texts_to_embed:
            try:
                # DashScope批量限制为10
                batch_size = 10
                for batch_start in range(0, len(texts_to_embed), batch_size):
                    batch_end = min(batch_start + batch_size, len(texts_to_embed))
                    batch = texts_to_embed[batch_start:batch_end]

                    response = requests.post(
                        "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "input": {"texts": batch}
                        },
                        timeout=60
                    )

                    if response.status_code != 200:
                        print(f"[Embedding] Batch API error: {response.status_code}, {response.text}")
                        continue

                    result = response.json()
                    # DashScope返回格式: {"output": {"embeddings": [{"embedding": [...], "text_index": 0}, ...]}}
                    embeddings_data = result["output"]["embeddings"]

                    for j, emb_data in enumerate(embeddings_data):
                        idx = indices_to_embed[batch_start + j]
                        results[idx] = emb_data["embedding"]

                        # 写入缓存
                        if use_cache and redis:
                            redis.cache_embedding(
                                self._text_hash(texts[idx]),
                                emb_data["embedding"]
                            )

            except Exception as e:
                print(f"[Embedding] 批量向量化失败: {e}")

        return results

    def embed_for_milvus(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入文本用于Milvus存储（总是返回有效向量）

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        embeddings = self.embed_batch(texts)

        # 确保返回正确的维度（如果失败则用零向量）
        zero_embedding = [0.0] * self.dimension
        return [e if e is not None else zero_embedding for e in embeddings]


# 单例模式全局实例
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """获取Embedding服务单例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
