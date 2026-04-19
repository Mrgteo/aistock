"""
RAG 服务 - 检索增强生成核心服务
参考 RagFlow 优化: 混合检索、引用标注、语义分块
"""
import os
import re
import math
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
        self._rerank = None

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

    def _get_rerank(self):
        if self._rerank is None:
            try:
                from backend.services.rerank_service import get_rerank_service
                self._rerank = get_rerank_service()
            except Exception:
                pass
        return self._rerank

    def _get_embedding(self):
        if self._embedding is None:
            from backend.services.embedding_service import get_embedding_service
            self._embedding = get_embedding_service()
        return self._embedding

    def _filter_watermark(self, text: str) -> str:
        """过滤文本中的水印信息"""
        if not text:
            return text
        import re
        # 过滤常见水印模式
        patterns = [
            r'国际资本市场研报资讯\+V:\s*\w+',
            r'## 知识星球 全球资讯精读',
            r'知识星球[^\n]*',
            r'清新研究团队[^\n]*',
            r'入宝藏群请加\s*quanqiuzixun8',
            r'入宝藏群请加',
            r'免责声明[^\n]*',
            r'仅限[^\n]*学习交流[^\n]*',
            r'^：',  # 开头的水印冒号
            r'^先见AI[^\n]*',
            r'有料有据的商业分析智能体[^\n]*',
            r'## 全球资讯精读',
            r'C 知识星球',
            r'@清新研究团队简介',
            r'<div style="text-align: center;">.*?</div>',  # 图片div标签
            r'imgs/img_in_image_box_\d+_\d+_\d+_\d+\.jpg',
            r'\({img in image box \d+}_\d+_\d+_\d+_\d+\)',  # Image references
            r'\(微信.+\)',  # WeChat references
            r'每月持续更新5000\+行业研究报告[^\n]*',
            r'实时精选全球最新财经资讯[^\n]*',
            r'挖掘国际财经内幕[^\n]*',
            r'涉及私募股权[^\n]*',
            r'提供研报专业定制服务[^\n]*',
        ]
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)
        # 清理多余空白和换行
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text

    def _clean_chunk_text(self, text: str) -> str:
        """
        清理文本块中的格式符号和残留水印

        清理内容：
        1. Markdown标题符号 ##, #
        2. 列表符号 •, -, *, 数字.
        3. 多余的括号和特殊符号
        4. 残留的水印模式
        5. 清理多余空白
        """
        if not text:
            return text

        # 0. 移除 HTML 标签（处理丢失标签前缀的情况如 src="..." 或 />）
        text = re.sub(r'<[^>]+>', '', text)  # 移除所有完整HTML标签
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)  # 移除HTML实体
        # 移除孤立的HTML属性片段（如被截断的标签 rc="", width="" 等）
        text = re.sub(r'(?:src|href|width|height|alt|id|class|style|align|valign)="[^"]*"', '', text)
        # 移除 /> 自闭合符号及之前的残留
        text = re.sub(r'[a-zA-Z-]+="[^"]*"\s*/>', '', text)
        text = re.sub(r'/\s*>', '', text)
        # 移除孤立的 rc= imgs= 属性名（img标签被截断的情况）
        text = re.sub(r'\s*rc="[^"]*"', '', text)
        text = re.sub(r'\s*imgs="[^"]*"', '', text)
        # 移除 HTML 属性片段如 style=', align=, '> 等
        text = re.sub(r"[a-zA-Z]+='[^']*'", '', text)  # style='...'
        text = re.sub(r"[a-zA-Z]+=\"[^\"]*\"", '', text)  # style="..."
        text = re.sub(r";'>", '', text)  # end of style attr
        text = re.sub(r"'\s*>", '', text)  # end of style tag
        text = re.sub(r'td\s+style=', ' ', text)  # td style=
        text = re.sub(r'<td\s+', ' ', text)  # <td with attributes
        text = re.sub(r'<\s*$', '', text, flags=re.MULTILINE)  # 移除行尾孤立的 <
        text = re.sub(r'>\s*$', '', text, flags=re.MULTILINE)  # 移除行尾孤立的 >

        # 1. 移除 Markdown 标题符号 ## 和 # (行首的)
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

        # 2. 移除列表符号 •, -, *, +, 数字编号 (行首的)
        text = re.sub(r'^[\s]*[•\-\*\+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

        # 3. 移除水印标记 (C ## @ 风格 - 跨行的水印标记)
        text = re.sub(r'\([\s\n]*[A-Z][\s\n]*#{1,3}[\s\n]*[@#]*[\s\n]*[^\)\n]{0,30}(?:[\n]|$)', '', text)
        # 4. 移除 (C##...) 完整括号水印
        text = re.sub(r'\([A-Z]#{1,3}[^)]*\)', '', text)
        # 5. 移除中文括号包裹的水印标记
        text = re.sub(r'[（【][\s\n]*[A-Z][\s\n]*#{1,3}[\s\n]*[@#]*[^\)】]*', '', text)
        text = re.sub(r'[）】]\s*$', '', text, flags=re.MULTILINE)

        # 6. 移除连续的特殊符号
        text = re.sub(r'[◆▇●]\s*', '', text)

        # 7. 移除水印模式（只匹配行首的完整水印短语，保留正文中的真实内容）
        watermark_patterns = [
            r'^## 知识星球 全球资讯精读',  # 完整水印标题
            r'^知识星球 全球资讯精读',      # 完整水印（无##）
            r'^全球资讯精读',              # 完整水印关键字
            r'^@清新研究团队简介',        # 完整水印
            r'^C\s*知识星球',             # C 知识星球 水印
            r'^先见AI[^\n]*',            # 先见AI水印
        ]
        for pattern in watermark_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)

        # 8. 清理多余空白和空行
        text = re.sub(r'[ \t]+', ' ', text)  # 多余空格
        text = re.sub(r'\n{3,}', '\n\n', text)  # 多余空行

        # 9. 移除孤立的水印符号（整行只有一个符号的情况）
        text = re.sub(r'^[\s]*[（】)]\s*$', '', text, flags=re.MULTILINE)  # 孤立中文括号
        text = re.sub(r'^@\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[A-Z]\s*$', '', text, flags=re.MULTILINE)  # 孤立单字母
        text = re.sub(r'^#+\s*$', '', text, flags=re.MULTILINE)  # 孤立#

        # 10. 移除首尾空白和空行
        text = text.strip()

        return text

    def _get_report_service(self):
        if self._report_service is None:
            from backend.services.report_service import get_report_service
            self._report_service = get_report_service()
        return self._report_service

    # ========== 报告处理流程 ==========

    async def process_report(self, report_id: str, file_data: bytes,
                            filename: str, do_vectorize: bool = False) -> Dict[str, Any]:
        """
        处理上传的报告

        Args:
            report_id: 报告ID
            file_data: 文件二进制数据
            filename: 文件名
            do_vectorize: 是否向量化存储（上传分析模块不需要，知识库模块需要）

        Returns:
            处理结果
        """
        try:
            mongodb = self._get_mongodb()
            report_service = self._get_report_service()

            # 更新状态：处理中
            mongodb.update_report_status(report_id, "processing")

            # 1. 提取文本
            print(f"[RagService] 开始提取文本: {filename}")
            full_text, pages_text = report_service.extract_text(file_data, filename)

            if not full_text:
                mongodb.update_report_status(report_id, "failed")
                return {"success": False, "error": "无法提取文本内容"}

            # 2. 文本分块（仅当需要向量化时）
            chunks = []
            if do_vectorize:
                chunks = report_service.chunk_text(full_text, pages_text)
                if not chunks:
                    mongodb.update_report_status(report_id, "failed")
                    return {"success": False, "error": "文本分块失败"}

                # 3. 向量化
                print(f"[RagService] 开始向量化 {len(chunks)} 个块")
                embedding = self._get_embedding()
                texts = [c["text"] for c in chunks]
                embeddings = embedding.embed_for_milvus(texts)

                # 4. 存储到Chroma
                chroma = self._get_chroma()
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

            # 5. 更新MongoDB（存储原始文本和分块信息）
            mongodb.update_report_content(
                report_id,
                full_text,
                [{"chunk_id": c["chunk_id"], "text": c["text"],
                  "page": c.get("page", 0)} for c in chunks] if chunks else [],
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
                               use_rag: bool = True,
                               top_k: int = 5) -> Dict[str, Any]:
        """
        使用RAG进行报告分析

        Args:
            report_id: 报告ID
            query: 分析查询
            use_knowledge_base: 是否使用知识库（仅AI研报问答模块使用）
            use_rag: 是否使用RAG检索（上传分析模块设为false）
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

            # 2. RAG检索（上传分析模块不使用RAG，直接分析报告内容）
            context = ""
            relevant_chunks = []
            if use_rag:
                relevant_chunks = await self.retrieve(
                    query,
                    collection="report_chunks",
                    top_k=top_k,
                    report_id=report_id
                )
                context = self.build_context(relevant_chunks)

                # 3. 知识库检索（可选）
                kb_chunks = []
                if use_knowledge_base:
                    kb_chunks = await self.retrieve(
                        query,
                        collection="knowledge_chunks",
                        top_k=top_k
                    )
                if kb_chunks:
                    kb_context = self.build_context(kb_chunks)
                    context += "\n\n【相关知识库内容】\n" + kb_context

            # 4. 调用AI分析（上传分析直接传完整报告文本）
            ai_response = await self._call_deepseek_analyze(
                report_title=report.get("title", ""),
                query=query,
                context=context,
                report_text=report.get("content_text", "")[:8000]
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
                    for c in (relevant_chunks if relevant_chunks else [])[:3]
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
                               filename: str, tags: List[str] = None,
                               mongodb=None) -> Dict[str, Any]:
        """
        处理上传的知识库文件

        Args:
            kb_id: 知识库ID
            file_data: 文件数据
            filename: 文件名
            tags: 标签
            mongodb: 可选的MongoDB服务实例（后台任务传入以避免初始化问题）

        Returns:
            处理结果
        """
        try:
            # 优先使用传入的mongodb实例
            if mongodb is None:
                mongodb = self._get_mongodb()
            chroma = self._get_chroma()
            embedding = self._get_embedding()
            report_service = self._get_report_service()

            # 更新进度：开始提取文本
            self._update_progress(kb_id, "extracting", 0, "正在提取文本...", mongodb)

            # 1. 提取文本
            full_text, _ = report_service.extract_text(file_data, filename)

            if not full_text:
                self._update_progress(kb_id, "failed", 0, "无法提取文本", mongodb)
                return {"success": False, "error": "无法提取文本"}

            # 更新进度：文本提取完成，开始分块
            self._update_progress(kb_id, "chunking", 30, "正在分块文本...", mongodb)

            # 2. 文本分块
            chunks = report_service.chunk_text(full_text)

            if not chunks:
                self._update_progress(kb_id, "failed", 0, "文本分块失败", mongodb)
                return {"success": False, "error": "文本分块失败"}

            # 更新进度：分块完成，开始过滤空块
            self._update_progress(kb_id, "filtering", 40, "正在过滤空内容块...", mongodb)

            # 3. 过滤空块：清洗文本后丢弃过短的块
            filtered_chunks = []
            for c in chunks:
                filtered_text = self._filter_watermark(c["text"])
                filtered_text = self._clean_chunk_text(filtered_text)
                if filtered_text and len(filtered_text.strip()) >= 10:
                    filtered_chunks.append({
                        "chunk_id": c["chunk_id"],
                        "text": filtered_text,
                        "page": c.get("page", 0),
                        "embedding_index": chunks.index(c)  # 记录原始索引用于向量获取
                    })

            print(f"[RagService] 过滤后保留 {len(filtered_chunks)}/{len(chunks)} 个块")

            if not filtered_chunks:
                self._update_progress(kb_id, "failed", 0, "所有内容块均为水印或空内容", mongodb)
                return {"success": False, "error": "所有内容块均为水印或空内容"}

            # 更新进度：开始向量化
            self._update_progress(kb_id, "vectorizing", 50, f"正在向量化 {len(filtered_chunks)} 个块...", mongodb)

            # 4. 向量化（只对过滤后的块）
            texts_for_embedding = [c["text"] for c in filtered_chunks]
            embeddings = embedding.embed_for_milvus(texts_for_embedding)

            # 更新进度：向量化完成，开始索引
            self._update_progress(kb_id, "indexing", 80, "正在存储到向量数据库...", mongodb)

            # 5. 存储到Chroma
            vectors_to_insert = []
            for i, chunk in enumerate(filtered_chunks):
                vectors_to_insert.append({
                    "id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "report_id": kb_id,
                    "page": 0,
                    "chunk_index": i,
                    "metadata": {"tags": tags or [], "source": "knowledge_base", "title": filename},
                    "embedding": embeddings[i]
                })

            chroma.insert_vectors("knowledge_chunks", vectors_to_insert)

            # 更新进度：索引完成，更新MongoDB
            self._update_progress(kb_id, "saving", 95, "正在保存结果...", mongodb)

            # 6. 更新MongoDB（存储清洗后的分块信息）
            # 移除临时字段，只保留需要的数据
            final_chunks = []
            for c in filtered_chunks:
                final_chunks.append({
                    "chunk_id": c["chunk_id"],
                    "text": c["text"],
                    "page": c.get("page", 0)
                })

            vector_ids = [c["chunk_id"] for c in final_chunks]
            mongodb.update_knowledge_content(
                kb_id,
                full_text,
                final_chunks,
                vector_ids,
                "indexed"
            )

            # 清除进度
            self._clear_progress(kb_id, mongodb)

            return {
                "success": True,
                "kb_id": kb_id,
                "chunks_count": len(chunks)
            }

        except Exception as e:
            print(f"[RagService] 处理知识库失败: {e}")
            import traceback
            traceback.print_exc()
            self._update_progress(kb_id, "failed", 0, f"处理失败: {str(e)}", mongodb)
            return {"success": False, "error": str(e)}

    def _update_progress(self, kb_id: str, stage: str, progress: int, message: str, mongodb=None):
        """更新解析进度到MongoDB"""
        try:
            if mongodb is None:
                mongodb = self._get_mongodb()
            if mongodb is None:
                print(f"[RagService] _get_mongodb returned None, skipping progress update")
                return
            mongodb.update_knowledge_progress(kb_id, {
                "stage": stage,
                "progress": progress,
                "message": message
            })
            print(f"[RagService] Progress updated: kb={kb_id}, stage={stage}, progress={progress}, message={message}")
        except Exception as e:
            print(f"[RagService] _update_progress failed: {e}")

    def _clear_progress(self, kb_id: str, mongodb=None):
        """清除解析进度"""
        try:
            if mongodb is None:
                mongodb = self._get_mongodb()
            if mongodb is None:
                print(f"[RagService] _get_mongodb returned None, skipping clear progress")
                return
            mongodb.clear_knowledge_progress(kb_id)
            print(f"[RagService] Progress cleared: kb={kb_id}")
        except Exception as e:
            print(f"[RagService] _clear_progress failed: {e}")

    async def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        检索知识库（带Rerank重排序 + 混合检索）

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            检索结果，包含chunk_id用于引用标注
        """
        # 1. 查询预处理
        query = self._preprocess_query(query)

        # 2. 扩大检索范围获取更多候选
        candidate_k = min(top_k * 3, 20)

        # 3. 混合检索（向量 + BM25）
        results = await self._hybrid_search(query, "knowledge_chunks", top_k=candidate_k)

        if not results:
            return []

        # 4. Rerank重排序
        rerank = self._get_rerank()
        if rerank:
            # 提取文本和原始索引
            texts = [r.get("text", "") for r in results]
            reranked = rerank.rerank(query, texts, top_n=top_k)

            # 重新组织结果
            reranked_results = []
            seen_contents = set()  # 用于去重
            for r in reranked:
                idx = r["index"]
                if 0 <= idx < len(results):
                    item = results[idx].copy()
                    content = self._clean_chunk_text(self._filter_watermark(item.get("text", "")))

                    # 去重：跳过内容相似度超过80%的结果
                    content_hash = content[:100]  # 用前100字符作为哈希
                    if content_hash in seen_contents:
                        continue
                    seen_contents.add(content_hash)

                    item["relevance_score"] = r["relevance_score"]
                    item["content"] = content
                    item["chunk_id"] = item.get("id", "")
                    metadata = item.get("metadata", {})
                    item["title"] = metadata.get("title") or "文档"
                    reranked_results.append(item)
            results = reranked_results
        else:
            # 无rerank服务，直接过滤水印并清理格式
            seen_contents = set()
            deduplicated = []
            for r in results:
                content = self._clean_chunk_text(self._filter_watermark(r.get("text", "")))
                content_hash = content[:100]
                if content_hash in seen_contents:
                    continue
                seen_contents.add(content_hash)

                metadata = r.get("metadata", {})
                r["title"] = metadata.get("title") or "文档"
                r["content"] = content
                r["chunk_id"] = r.get("id", "")
                deduplicated.append(r)
            results = deduplicated

        return results

    async def synthesize_answer(self, query: str, context: str,
                               references: List[Dict] = None,
                               use_citations: bool = False) -> Dict:
        """
        基于检索到的上下文，调用LLM综合回答问题

        Args:
            query: 用户问题
            context: 检索到的上下文文本（字符串格式）
            references: 参考资料列表（当 use_citations=True 时使用）
            use_citations: 是否使用引用标注模式

        Returns:
            综合回答结果
        """
        # 如果有参考资料且启用引用模式，使用新的引用方法
        if use_citations and references:
            return await self.synthesize_answer_with_citations(query, references)

        try:
            llm_service = self._get_llm()
            if not llm_service:
                return {"success": False, "error": "LLM服务不可用"}

            # 构建系统提示
            system_prompt = """你是一位专业的金融分析师，擅长基于提供的参考资料回答用户关于金融市场的问题。

请遵循以下规则：
1. 基于提供的参考资料，用自己的语言综合回答用户问题，不要直接复制原文
2. 回答要有条理，使用列表或分点说明让内容清晰易读
3. 如果资料不足以完整回答，请明确指出哪些方面有资料支撑，哪些方面资料不足
4. 保持专业、客观的分析风格
5. 回答控制在500字以内，简洁有力
6. 只回答与问题相关的内容，不要跑题"""

            user_prompt = f"""用户问题：{query}

参考资料：
{self._filter_watermark(context)}

请基于以上参考资料，用自己的语言综合回答用户问题。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            answer = await llm_service.call_api_async(messages, max_tokens=2000, temperature=0.7)

            return {
                "success": True,
                "answer": answer
            }

        except Exception as e:
            print(f"[RagService] 综合回答失败: {e}")
            return {"success": False, "error": str(e)}

    def _get_llm(self):
        """获取LLM服务"""
        try:
            from backend.services.llm_service import get_llm_service
            return get_llm_service()
        except Exception:
            return None

    # ========== 查询预处理 ==========

    def _preprocess_query(self, query: str) -> str:
        """
        查询预处理：清理和规范化用户查询

        Args:
            query: 原始查询

        Returns:
            处理后的查询
        """
        if not query:
            return query

        # 移除多余空白
        query = re.sub(r'\s+', ' ', query).strip()

        # 移除特殊字符（保留中文、英文、数字）
        query = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', query)

        return query

    def _expand_query(self, query: str) -> List[str]:
        """
        查询扩展：生成同义词/相关词扩展

        Args:
            query: 原始查询

        Returns:
            扩展后的查询列表
        """
        # 金融领域同义词映射
        synonyms = {
            "股票": ["A股", "上市公司", "证券"],
            "牛市": ["上涨", "多头", "行情好"],
            "熊市": ["下跌", "空头", "行情差"],
            "利好": ["好消息", "正面", "受益"],
            "利空": ["坏消息", "负面", "风险"],
            "买入": ["增持", "推荐", "超配", "买入评级"],
            "卖出": ["减持", "回避", "卖出评级"],
            "AI": ["人工智能", "大模型", "机器学习"],
            "算力": ["计算", "芯片", "GPU"],
            "云计算": ["云服务", "IDC", "数据中心"],
            "新能源": ["电动车", "光伏", "储能"],
        }

        expanded = [query]
        words = query.split()
        for word in words:
            if word in synonyms:
                expanded.extend(synonyms[word])

        # 去重
        seen = set()
        result = []
        for w in expanded:
            if w not in seen:
                seen.add(w)
                result.append(w)

        return result[:5]  # 最多返回5个扩展查询

    # ========== BM25 关键词检索 ==========

    def _compute_bm25(self, query: str, documents: List[Dict],
                      k1: float = 1.5, b: float = 0.75) -> List[Dict]:
        """
        BM25 算法计算文档相关性分数

        Args:
            query: 查询文本
            documents: 文档列表 (每项包含 text 字段)
            k1: 词频饱和参数
            b: 文档长度归一化参数

        Returns:
            按相关性排序的文档列表
        """
        if not documents:
            return []

        # 分词（简单按字符/空格分）
        query_terms = self._tokenize(query)
        if not query_terms:
            return documents

        # 计算平均文档长度
        doc_lengths = []
        for doc in documents:
            text = doc.get("text", "")
            tokens = self._tokenize(text)
            doc_lengths.append(len(tokens))

        avg_dl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1

        # 统计词频
        doc_term_freqs = []
        for doc in documents:
            tokens = self._tokenize(doc.get("text", ""))
            freq = {}
            for term in tokens:
                freq[term] = freq.get(term, 0) + 1
            doc_term_freqs.append(freq)

        # 统计文档频率 (有多少文档包含该词)
        doc_freqs = {}
        for freq in doc_term_freqs:
            for term in freq:
                doc_freqs[term] = doc_freqs.get(term, 0) + 1

        n = len(documents)

        # 计算每个文档的 BM25 分数
        scores = []
        for i, doc in enumerate(documents):
            score = 0.0
            freq = doc_term_freqs[i]

            for term in query_terms:
                if term not in freq:
                    continue

                tf = freq[term]
                df = doc_freqs.get(term, 0)

                # IDF (避免除零)
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)

                # TF component
                tf_component = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_lengths[i] / avg_dl))

                score += idf * tf_component

            scores.append(score)

        # 按分数排序
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        # 返回排序后的文档
        result = []
        for idx, score in indexed_scores:
            doc = documents[idx].copy()
            doc["bm25_score"] = score
            result.append(doc)

        return result

    def _tokenize(self, text: str) -> List[str]:
        """
        简单分词：按空格和标点分割

        Args:
            text: 文本

        Returns:
            词语列表
        """
        if not text:
            return []

        # 转为小写（英文）
        text_lower = text.lower()

        # 按空格和标点分割
        tokens = re.split(r'[\s,.!?;:，。！？；：、""''（）【】《》]+', text_lower)

        # 过滤空字符串和单个字符
        tokens = [t for t in tokens if len(t) >= 2]

        return tokens

    async def _hybrid_search(self, query: str, collection: str,
                            top_k: int = 5, report_id: str = None) -> List[Dict]:
        """
        混合检索：结合向量检索和 BM25 关键词检索

        Args:
            query: 查询文本
            collection: 集合名称
            top_k: 返回数量
            report_id: 可选，限定报告ID

        Returns:
            混合检索结果
        """
        # 1. 向量检索
        vector_results = await self.retrieve(query, collection, top_k=top_k * 2, report_id=report_id)

        # 2. 如果 Chroma 支持获取所有文档，进行 BM25 检索
        #    否则使用简化版的关键词匹配
        bm25_results = []
        try:
            chroma = self._get_chroma()
            collection_obj = chroma.get_collection(collection)
            if collection_obj:
                # 获取集合中所有文档（限制数量避免过大，最多1000条）
                max_docs = 1000
                all_docs = collection_obj.get(include=["documents", "metadatas"], limit=max_docs)
                if all_docs and all_docs.get("documents"):
                    docs_for_bm25 = []
                    for i, doc_text in enumerate(all_docs["documents"]):
                        meta = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
                        # 如果指定了报告ID，只保留该报告的文档
                        if report_id and meta.get("report_id") != report_id:
                            continue
                        docs_for_bm25.append({
                            "id": all_docs["ids"][i] if "ids" in all_docs else str(i),
                            "text": doc_text,
                            "metadata": meta
                        })

                    # 计算 BM25 分数
                    bm25_results = self._compute_bm25(query, docs_for_bm25)
        except Exception as e:
            print(f"[RagService] BM25检索失败: {e}")

        # 3. 合并结果 (RRF融合)
        fused = self._reciprocal_rank_fusion([vector_results, bm25_results], k=60)

        return fused[:top_k]

    def _reciprocal_rank_fusion(self, result_lists: List[List[Dict]], k: int = 60) -> List[Dict]:
        """
        倒数排名融合 (RRF)：合并多个检索结果

        Args:
            result_lists: 多个检索结果列表
            k: RRF 参数

        Returns:
            融合后的结果列表
        """
        scores = {}

        for result_list in result_lists:
            if not result_list:
                continue
            for rank, item in enumerate(result_list):
                item_id = item.get("id") or item.get("chunk_id")
                if not item_id:
                    continue

                # RRF 分数
                score = 1.0 / (k + rank + 1)
                scores[item_id] = scores.get(item_id, 0) + score

                # 保留文档信息（只保留第一次的）
                if item_id not in [r.get("_merged_id") for r in scores if isinstance(r, dict)]:
                    pass

        # 按分数排序
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        result_map = {}
        for result_list in result_lists:
            for item in result_list:
                item_id = item.get("id") or item.get("chunk_id")
                if item_id:
                    result_map[item_id] = item

        fused_results = []
        for item_id, score in sorted_items:
            if item_id in result_map:
                item = result_map[item_id].copy()
                item["fused_score"] = score
                fused_results.append(item)

        return fused_results

    # ========== 带引用的综合回答 ==========

    async def synthesize_answer_with_citations(self, query: str,
                                              references: List[Dict]) -> Dict:
        """
        基于检索到的上下文，调用LLM综合回答问题（带引用标注）

        Args:
            query: 用户问题
            references: 参考资料列表（包含 chunk_id, text, title 等）

        Returns:
            综合回答结果（包含带引用的答案）
        """
        try:
            llm_service = self._get_llm()
            if not llm_service:
                return {"success": False, "error": "LLM服务不可用"}

            # 构建带引用的上下文
            context_parts = []
            ref_map = {}  # 用于追踪引用

            for i, ref in enumerate(references):
                chunk_id = ref.get("chunk_id") or ref.get("id", f"ref_{i}")
                title = ref.get("title", "文档")
                text = self._filter_watermark(ref.get("text", ""))

                # 创建引用标记 [cite:0], [cite:1], ...
                cite_marker = f"[cite:{i}]"
                ref_map[cite_marker] = {
                    "chunk_id": chunk_id,
                    "title": title,
                    "index": i
                }

                context_parts.append(f"{cite_marker}【{title}】\n{text[:500]}...")

            context_with_refs = "\n\n".join(context_parts)

            # 构建系统提示
            system_prompt = """你是一位专业的金融分析师，擅长基于提供的参考资料回答用户关于金融市场的问题。

请遵循以下规则：
1. 基于提供的参考资料，用自己的语言综合回答用户问题，不要直接复制原文
2. 回答要有条理，使用列表或分点说明让内容清晰易读
3. 在适当的位置插入引用标记 [cite:N]，其中 N 是参考资料编号
4. 引用示例：如果回答中使用了第2条参考资料的内容，插入 [cite:1]（从0开始编号）
5. 每个核心观点或数据尽量都标注引用来源
6. 如果资料不足以完整回答，请明确指出哪些方面有资料支撑
7. 保持专业、客观的分析风格
8. 回答控制在500字以内，简洁有力"""

            user_prompt = f"""用户问题：{query}

参考资料：
{context_with_refs}

请基于以上参考资料，在适当位置插入引用标记 [cite:N]，然后用自己的语言综合回答用户问题。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            answer = await llm_service.call_api_async(messages, max_tokens=2000, temperature=0.7)

            # 解析答案中的引用，替换为完整引用信息
            answer_with_citations = self._format_citations(answer, ref_map)

            return {
                "success": True,
                "answer": answer_with_citations,
                "answer_plain": answer,  # 原始答案（不含HTML格式的引用）
                "references": [
                    {
                        "index": info["index"],
                        "chunk_id": info["chunk_id"],
                        "title": info["title"]
                    }
                    for info in ref_map.values()
                ]
            }

        except Exception as e:
            print(f"[RagService] 带引用综合回答失败: {e}")
            return {"success": False, "error": str(e)}

    def _format_citations(self, answer: str, ref_map: Dict) -> str:
        """
        将答案中的 [cite:N] 标记转换为带样式的引用格式

        Args:
            answer: 原始答案
            ref_map: 引用映射

        Returns:
            带HTML引用的答案
        """
        if not ref_map:
            return answer

        def replace_cite(match):
            cite_key = match.group(0)
            if cite_key in ref_map:
                info = ref_map[cite_key]
                return f'<sup class="citation" data-chunk-id="{info["chunk_id"]}" data-title="{info["title"]}">[{info["index"] + 1}]</sup>'
            return cite_key

        # 替换所有引用标记
        formatted = re.sub(r'\[cite:\d+\]', replace_cite, answer)

        return formatted


# 单例模式
_rag_service: Optional[RagService] = None

def get_rag_service() -> RagService:
    """获取RAG服务单例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
