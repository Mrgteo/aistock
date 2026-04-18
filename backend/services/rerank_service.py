"""
Rerank 服务 - 使用 DashScope TextReRank 进行文档重排序
"""
import os
from typing import List, Dict, Optional, Tuple


class RerankService:
    """文档重排序服务"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model or os.getenv("DASHSCOPE_RERANK_MODEL", "gte-rerank")

        # 设置DashScope API key（DashScope SDK需要全局设置）
        if self.api_key:
            import dashscope
            dashscope.api_key = self.api_key

    def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[Dict]:
        """
        对文档进行重排序

        Args:
            query: 查询文本
            documents: 文档列表
            top_n: 返回数量

        Returns:
            重排序结果列表，每项包含 index, relevance_score, document
        """
        if not documents or not query.strip():
            return []

        try:
            from dashscope import TextReRank

            response = TextReRank.call(
                model=self.model,
                query=query,
                documents=documents,
                return_documents=True,
                top_n=min(top_n, len(documents))
            )

            if response.status_code != 200:
                print(f"[Rerank] API error: {response.code}, {response.message}")
                return self._fallback_rerank(query, documents, top_n)

            results = []
            for result in response.output.results:
                results.append({
                    "index": result.index,
                    "relevance_score": result.relevance_score,
                    "document": result.document.text if hasattr(result, 'document') and result.document else documents[result.index]
                })

            # 按 relevance_score 降序排序
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            return results[:top_n]

        except Exception as e:
            print(f"[Rerank] Exception: {e}")
            return self._fallback_rerank(query, documents, top_n)

    def _fallback_rerank(self, query: str, documents: List[str], top_n: int) -> List[Dict]:
        """后备重排序方案：基于关键词匹配"""
        import re

        # 提取查询关键词
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,10}|[a-zA-Z]{2,20}|\d{6}', query.lower())

        scores = []
        for i, doc in enumerate(documents):
            doc_lower = doc.lower()
            # 计算关键词命中数
            match_count = sum(1 for kw in keywords if kw in doc_lower)
            # 计算命中密度
            score = match_count / max(len(keywords), 1) if keywords else 0.5
            scores.append((i, score, doc))

        # 按得分降序
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score, doc in scores[:top_n]:
            results.append({
                "index": idx,
                "relevance_score": score,
                "document": doc
            })

        return results

    def similarity(self, query: str, documents: List[str]) -> Tuple[List[float], int]:
        """
        计算查询与文档的相似度分数

        Args:
            query: 查询文本
            documents: 文档列表

        Returns:
            (相似度分数列表, 使用的token数)
        """
        if not documents:
            return [], 0

        results = self.rerank(query, documents, top_n=len(documents))
        if not results:
            return [0.0] * len(documents), 0

        # 按原始顺序排列分数
        scores = [0.0] * len(documents)
        for r in results:
            if 0 <= r["index"] < len(documents):
                scores[r["index"]] = r["relevance_score"]

        return scores, sum(len(d) for d in documents) // 4  # 粗略估算token


# 单例模式全局实例
_rerank_service: Optional[RerankService] = None


def get_rerank_service() -> RerankService:
    """获取Rerank服务单例"""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service
