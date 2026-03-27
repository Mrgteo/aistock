"""
RAG 服务 - 检索增强生成核心服务
"""
import os
import re
from typing import List, Dict, Optional, Any
from datetime import datetime


def strip_markdown(text: str) -> str:
    """去除markdown格式，保留结构化内容"""
    if not text:
        return text

    # 先转换表格为HTML
    text = convert_markdown_tables(text)

    # 移除代码块标记（保留内容）
    text = re.sub(r'```[\w]*\n?', '', text)
    text = re.sub(r'```', '', text)
    # 移除行内代码标记
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # 转换粗体
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
    # 转换斜体
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
    # 移除删除线
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    # 移除标题标记，转换为加粗标题样式
    text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    # 移除链接，保留文本
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 移除图片
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    # 转换引用
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    # 转换列表项
    text = re.sub(r'^[\s]*[-*+]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', r'\n', text, flags=re.MULTILINE)
    # 移除水平线
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def convert_markdown_tables(text: str) -> str:
    """将markdown表格转换为HTML表格"""
    lines = text.split('\n')
    result = []
    in_table = False
    table_rows = []
    header_row = None
    col_aligns = []

    for line in lines:
        # 检测表格行
        if '|' in line and line.strip().startswith('|'):
            # 检查是否是分隔行 (|---|---|)
            if re.match(r'^\|[\s\-:|]+\|$', line):
                # 解析对齐方式
                parts = line.split('|')[1:-1]
                for part in parts:
                    part = part.strip()
                    if part.startswith(':') and part.endswith(':'):
                        col_aligns.append('center')
                    elif part.endswith(':'):
                        col_aligns.append('right')
                    else:
                        col_aligns.append('left')
                continue

            # 解析表格行
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if not in_table:
                in_table = True
                header_row = cells
            else:
                table_rows.append(cells)
        else:
            if in_table and header_row:
                # 生成HTML表格
                align_styles = ''
                if col_aligns:
                    align_styles = ' style="text-align: left;"'
                    # 简化处理，使用统一的样式

                html = '<table style="border-collapse: collapse; width: 100%; margin: 10px 0;">\n'

                # 表头
                html += '<thead><tr>'
                for i, cell in enumerate(header_row):
                    style = f'text-align: {col_aligns[i] if i < len(col_aligns) else "left"}; background: #f1f5f9; padding: 8px; border: 1px solid #e2e8f0;'
                    html += f'<th style="{style}">{cell}</th>'
                html += '</tr></thead>\n'

                # 表体
                html += '<tbody>\n'
                for row in table_rows:
                    html += '<tr>'
                    for i, cell in enumerate(row):
                        style = f'text-align: {col_aligns[i] if i < len(col_aligns) else "left"}; padding: 8px; border: 1px solid #e2e8f0;'
                        html += f'<td style="{style}">{cell}</td>'
                    html += '</tr>\n'
                html += '</tbody>\n</table>'

                result.append(html)
                result.append('')  # 空行
                table_rows = []
                header_row = None
                col_aligns = []
                in_table = False
            result.append(line)

    # 处理最后可能未关闭的表格
    if in_table and header_row:
        html = '<table style="border-collapse: collapse; width: 100%; margin: 10px 0;">\n'
        html += '<thead><tr>'
        for i, cell in enumerate(header_row):
            html += f'<th style="background: #f1f5f9; padding: 8px; border: 1px solid #e2e8f0;">{cell}</th>'
        html += '</tr></thead>\n<tbody>\n'
        for row in table_rows:
            html += '<tr>'
            for cell in row:
                html += f'<td style="padding: 8px; border: 1px solid #e2e8f0;">{cell}</td>'
            html += '</tr>\n'
        html += '</tbody>\n</table>'
        result.append(html)

    return '\n'.join(result)


class RagService:
    """RAG核心服务类"""

    def __init__(self):
        self._mongodb = None
        self._chroma = None
        self._redis = None
        self._embedding = None
        self._report_service = None

    def _get_mongodb(self):
        if self._mongodb is None:
            from backend.services.mongodb_service import get_mongodb_service
            self._mongodb = get_mongodb_service()
        return self._mongodb

    def _get_chroma(self):
        if self._chroma is None:
            from backend.services.chroma_service import get_chroma_service
            self._chroma = get_chroma_service()
        return self._chroma

    def _get_redis(self):
        if self._redis is None:
            try:
                from backend.services.redis_service import get_redis_service
                self._redis = get_redis_service()
            except Exception:
                pass
        return self._redis

    def _get_embedding(self):
        if self._embedding is None:
            from backend.services.embedding_service import get_embedding_service
            self._embedding = get_embedding_service()
        return self._embedding

    def _get_report_service(self):
        if self._report_service is None:
            from backend.services.report_service import get_report_service
            self._report_service = get_report_service()
        return self._report_service

    # ========== 报告处理流程 ==========

    async def process_report(self, report_id: str, file_data: bytes,
                            filename: str) -> Dict[str, Any]:
        """
        处理上传的报告

        Args:
            report_id: 报告ID
            file_data: 文件二进制数据
            filename: 文件名

        Returns:
            处理结果
        """
        try:
            mongodb = self._get_mongodb()
            chroma = self._get_chroma()
            embedding = self._get_embedding()
            report_service = self._get_report_service()

            # 更新状态：处理中
            mongodb.update_report_status(report_id, "processing")

            # 1. 提取文本
            print(f"[RagService] 开始提取文本: {filename}")
            full_text, pages_text = report_service.extract_text(file_data, filename)

            if not full_text:
                mongodb.update_report_status(report_id, "failed")
                return {"success": False, "error": "无法提取文本内容"}

            # 2. 文本分块
            chunks = report_service.chunk_text(full_text, pages_text)

            if not chunks:
                mongodb.update_report_status(report_id, "failed")
                return {"success": False, "error": "文本分块失败"}

            # 3. 向量化
            print(f"[RagService] 开始向量化 {len(chunks)} 个块")
            texts = [c["text"] for c in chunks]
            embeddings = embedding.embed_for_milvus(texts)

            # 4. 存储到Chroma
            vectors_to_insert = []
            for i, chunk in enumerate(chunks):
                vectors_to_insert.append({
                    "id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "report_id": report_id,
                    "page": chunk.get("page", 0),
                    "chunk_index": i,
                    "metadata": chunk.get("metadata", {}),
                    "embedding": embeddings[i]
                })

            chroma.insert_vectors("report_chunks", vectors_to_insert)

            # 5. 更新MongoDB
            vector_ids = [c["chunk_id"] for c in chunks]
            mongodb.update_report_content(
                report_id,
                full_text,
                [{"chunk_id": c["chunk_id"], "text": c["text"],
                  "page": c.get("page", 0)} for c in chunks],
                "processed"
            )

            print(f"[RagService] 报告处理完成: {report_id}")

            return {
                "success": True,
                "report_id": report_id,
                "chunks_count": len(chunks),
                "text_length": len(full_text)
            }

        except Exception as e:
            print(f"[RagService] 处理报告失败: {e}")
            import traceback
            traceback.print_exc()

            # 更新状态
            try:
                self._get_mongodb().update_report_status(report_id, "failed")
            except:
                pass

            return {"success": False, "error": str(e)}

    # ========== 检索功能 ==========

    async def retrieve(self, query: str, collection: str = "report_chunks",
                      top_k: int = 5, report_id: str = None) -> List[Dict]:
        """
        检索相关文本块

        Args:
            query: 查询文本
            collection: 集合名称
            top_k: 返回数量
            report_id: 可选，限定报告ID

        Returns:
            检索结果列表
        """
        try:
            # 尝试从缓存获取
            redis = self._get_redis()
            if redis:
                cached = redis.get_cached_search(query, collection)
                if cached:
                    return cached

            # 获取查询向量
            embedding = self._get_embedding()
            query_vector = embedding.embed_text(query)

            if not query_vector:
                return []

            # Chroma检索
            chroma = self._get_chroma()
            results = chroma.search_vectors(
                collection,
                query_vector,
                top_k=top_k,
                report_id=report_id
            )

            # 缓存结果
            if redis and results:
                redis.cache_search_results(query, collection, results)

            return results

        except Exception as e:
            print(f"[RagService] 检索失败: {e}")
            return []

    def build_context(self, chunks: List[Dict], max_length: int = 4000) -> str:
        """
        构建RAG上下文

        Args:
            chunks: 检索到的文本块
            max_length: 最大上下文长度

        Returns:
            上下文字符串
        """
        if not chunks:
            return ""

        context_parts = []
        total_length = 0

        for chunk in chunks:
            text = chunk.get("text", "")
            page = chunk.get("page", 0)

            chunk_text = f"[来源：第{page}页]\n{text}\n"

            if total_length + len(chunk_text) > max_length:
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        return "\n".join(context_parts)

    # ========== AI分析功能 ==========

    async def analyze_with_rag(self, report_id: str, query: str,
                               use_knowledge_base: bool = True,
                               top_k: int = 5) -> Dict[str, Any]:
        """
        使用RAG进行报告分析

        Args:
            report_id: 报告ID
            query: 分析查询
            use_knowledge_base: 是否使用知识库
            top_k: 检索数量

        Returns:
            分析结果
        """
        try:
            mongodb = self._get_mongodb()
            embedding = self._get_embedding()

            # 1. 获取报告信息
            report = mongodb.get_report(report_id)
            if not report:
                return {"success": False, "error": "报告不存在"}

            # 2. RAG检索
            relevant_chunks = await self.retrieve(
                query,
                collection="report_chunks",
                top_k=top_k,
                report_id=report_id
            )

            # 3. 知识库检索（可选）
            kb_chunks = []
            if use_knowledge_base:
                kb_chunks = await self.retrieve(
                    query,
                    collection="knowledge_chunks",
                    top_k=top_k
                )

            # 4. 构建上下文
            context = self.build_context(relevant_chunks)
            if kb_chunks:
                kb_context = self.build_context(kb_chunks)
                context += "\n\n【相关知识库内容】\n" + kb_context

            # 5. 调用AI分析
            ai_response = await self._call_deepseek_analyze(
                report_title=report.get("title", ""),
                query=query,
                context=context,
                report_text=report.get("content_text", "")[:5000]
            )

            # 6. 提取股票和行业信息（从AI分析文本中提取，而非原始报告）
            # 先去除markdown格式再提取，避免格式符号干扰
            ai_text = strip_markdown(ai_response)
            # 去除HTML标签得到纯文本
            import re
            ai_text_plain = re.sub(r'<[^>]+>', '', ai_text)

            mentioned_stocks = self._get_report_service().extract_stocks_mentioned(ai_text_plain)
            mentioned_industries = self._get_report_service().extract_industries_mentioned(ai_text_plain)

            # 提取关键词
            keywords = self._get_report_service().extract_keywords(
                report.get("content_text", ""),
                top_k=5
            )

            # 7. 保存分析结果
            # 去除markdown格式
            ai_analysis_clean = strip_markdown(ai_response)

            result = {
                "mentioned_stocks": mentioned_stocks,
                "mentioned_industries": mentioned_industries,
                "keywords": keywords,
                "ai_analysis": ai_analysis_clean,
                "sources": [
                    {"chunk_id": c["id"], "text": c["text"][:200], "score": c["score"]}
                    for c in relevant_chunks[:3]
                ]
            }

            analysis_id = mongodb.save_analysis_result(
                report_id, query, result, ai_analysis_clean,
                report_title=report.get("title"),
                mentioned_stocks=mentioned_stocks,
                mentioned_industries=mentioned_industries
            )

            return {
                "success": True,
                "analysis_id": analysis_id,
                "report_title": report.get("title"),
                "keywords": keywords,
                **result
            }

        except Exception as e:
            print(f"[RagService] 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def _call_deepseek_analyze(self, report_title: str, query: str,
                                    context: str, report_text: str) -> str:
        """调用DeepSeek API进行AI分析"""
        import requests

        prompt = f"""你是一个专业的股票分析师。请根据以下信息分析这份研报。

报告标题：{report_title}

用户问题：{query}

相关文本片段：
{context}

请提供专业的分析，包括：
1. 报告核心观点
2. 涉及的A股标的（利好/利空）
3. 涉及的行业板块（利好/利空）
4. 投资建议

请用中文回答。"""

        try:
            api_key = os.getenv("DEEPSEEK_API_KEY", "sk-8cb3bfe75b94480a8005a87362306526")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": os.getenv("DEFAULT_MODEL_NAME", "deepseek-chat"),
                    "messages": [
                        {"role": "system", "content": "你是专业的股票分析助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"AI分析调用失败: {response.status_code}"

        except Exception as e:
            return f"AI分析调用异常: {str(e)}"

    # ========== 知识库处理 ==========

    async def process_knowledge(self, kb_id: str, file_data: bytes,
                               filename: str, tags: List[str] = None) -> Dict[str, Any]:
        """
        处理上传的知识库文件

        Args:
            kb_id: 知识库ID
            file_data: 文件数据
            filename: 文件名
            tags: 标签

        Returns:
            处理结果
        """
        try:
            mongodb = self._get_mongodb()
            chroma = self._get_chroma()
            embedding = self._get_embedding()
            report_service = self._get_report_service()

            # 1. 提取文本
            full_text, _ = report_service.extract_text(file_data, filename)

            if not full_text:
                return {"success": False, "error": "无法提取文本"}

            # 2. 文本分块
            chunks = report_service.chunk_text(full_text)

            # 3. 向量化
            texts = [c["text"] for c in chunks]
            embeddings = embedding.embed_for_milvus(texts)

            # 4. 存储到Chroma
            vectors_to_insert = []
            for i, chunk in enumerate(chunks):
                vectors_to_insert.append({
                    "id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "report_id": kb_id,
                    "page": 0,
                    "chunk_index": i,
                    "metadata": {"tags": tags or [], "source": "knowledge_base"},
                    "embedding": embeddings[i]
                })

            chroma.insert_vectors("knowledge_chunks", vectors_to_insert)

            # 5. 更新MongoDB
            vector_ids = [c["chunk_id"] for c in chunks]
            mongodb.update_knowledge_content(
                kb_id,
                full_text,
                [{"chunk_id": c["chunk_id"], "text": c["text"]} for c in chunks],
                vector_ids,
                "indexed"
            )

            return {
                "success": True,
                "kb_id": kb_id,
                "chunks_count": len(chunks)
            }

        except Exception as e:
            print(f"[RagService] 处理知识库失败: {e}")
            return {"success": False, "error": str(e)}

    async def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        检索知识库

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            检索结果
        """
        return await self.retrieve(query, "knowledge_chunks", top_k)


# 单例模式
_rag_service: Optional[RagService] = None

def get_rag_service() -> RagService:
    """获取RAG服务单例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
