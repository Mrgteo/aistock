# RAGFlow vs aistock RAG 系统对比分析

> 分析时间：2026-04-13
> 参考项目：RAGFlow (https://github.com/infiniflow/ragflow)

---

## 一、整体架构对比

| 维度 | RAGFlow | aistock |
|------|---------|---------|
| **架构模式** | 微服务 + Docker | 单体应用 |
| **向量数据库** | Elasticsearch / Infinity | ChromaDB |
| **文档解析** | 专业解析器工厂模式 | pdfplumber + python-docx |
| **分块策略** | 多种策略可选 | 固定500字符 + 50重叠 |
| **检索方式** | 混合检索(向量+全文) | 纯向量相似度 |
| **重排序** | 多Provider支持 | qwen3-rerank |
| **异步任务** | Redis队列 + task_executor | asyncio.create_task |
| **知识图谱** | GraphRAG支持 | 无 |
| **OCR能力** | PaddleOCR集成 | 无 |
| **多租户** | 完整支持 | 无 |

---

## 二、核心差距详解

### 1. 文档解析能力

**RAGFlow** (`/rag/app/naive.py`):
```python
# 多种专业解析器
FACTORY = {
    "general": naive, "paper": paper, "book": book,
    "presentation": presentation, "manual": manual,
    "laws": laws, "qa": qa, "table": table,
    "resume": resume, "picture": picture, ...
}
```
- PDF布局分析 (layout_recognizer)
- 表格结构识别 (table_structure_recognizer)
- OCR文字识别 (PaddleOCR)
- 支持图片、图表、公式

**aistock**:
- 仅 `pdfplumber` 简单文本提取
- 无布局分析，无法区分标题/正文/表格
- 无OCR能力，扫描PDF无法处理
- DOCX仅提取文本，格式丢失

---

### 2. 分块策略

**RAGFlow** (`/rag/nlp/__init__.py`):
```python
# 多种分块策略
naive_merge()          # 基于token的简单分块
tree_merge()           # 基于文档树结构
hierarchical_merge()   # 层级分块
naive_merge_docx()     # Word专用
```

**aistock** (`report_service.py`):
```python
chunk_size = 500       # 固定500字符
chunk_overlap = 50     # 固定50重叠
```

**问题分析**：
- 短段落被强行截断，语义不连贯
- 表格被拆散，丢失表格结构
- 中文句号分割不精准
- 无法识别文档结构（标题层级）

---

### 3. 检索策略

**RAGFlow** (`/rag/nlp/search.py`):
```python
# 混合检索
async def retrieval(
    question, embd_mdl, tenant_ids, kb_ids,
    vector_similarity_weight=0.3,  # 可配置权重
    similarity_threshold=0.2,
    rerank_mdl=None  # 可选重排序
):
    # 1. Dense检索 - 向量相似度
    # 2. Sparse检索 - BM25全文
    # 3. 混合融合 - weighted_sum
```

**aistock** (`chroma_service.py`):
```python
# 纯向量检索
collection.query(
    query_embeddings=[query_vector],
    n_results=top_k,
    where=where_filter,
    include=["documents", "metadatas", "distances"]
)
```

**问题分析**：
- 缺少全文检索能力
- 无法做混合检索
- 关键词精确匹配能力弱

---

### 4. 重排序

**RAGFlow**: 支持 12+ 种重排序模型
- Jina Rerank, Cohere, NVIDIA, QWen, HuggingFace, Voyage AI...

**aistock**: 仅 qwen3-rerank（已集成，可满足基本需求）

---

### 5. 异步任务处理

**RAGFlow** (`/rag/svr/task_executor.py`):
```python
# Redis队列 + 信号量限流
async def start():
    while True:
        task = await redis.brpop("chunk_queue")
        await chunk_limiter.acquire()
        asyncio.create_task(process_chunk(task))
```

**aistock**:
```python
# 简单异步任务，无队列
asyncio.create_task(process_knowledge_background(...))
```

**问题分析**：
- 大文件处理时阻塞主线程
- 无进度追踪
- 无失败重试机制
- 无任务状态查询

---

### 6. 知识图谱

**RAGFlow GraphRAG**:
- 实体抽取 (NER)
- 关系抽取
- 社区检测 (Leiden算法)
- 社区报告生成

**aistock**: 无此功能

---

## 三、可优化改进建议

### 高优先级

#### 1. 增强文档解析能力

```
建议添加:
- 布局分析识别（标题、段落、表格区域）
- 表格结构化处理（不是简单pipe分隔）
- OCR支持扫描PDF

参考实现:
- 引入 PaddleOCR
- 或集成 RAGFlow 的 deepdoc 模块
```

#### 2. 改进分块策略

```python
# 建议修改 report_service.py
def chunk_text(self, text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[Dict]:
    """改进版分块：基于段落，保留表格"""
    chunks = []

    # 按段落分割（保留段落结构）
    paragraphs = re.split(r'\n{2,}', text)

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 表格整块保留
        if '|' in para or '┌' in para:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            continue

        # 普通段落
        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # overlap处理
            overlap_text = current_chunk[-chunk_overlap:] if current_chunk else ""
            current_chunk = overlap_text + para + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [{"chunk_id": str(uuid.uuid4()), "text": c} for c in chunks]
```

#### 3. 添加混合检索

```python
# 在 rag_service.py 添加
async def hybrid_retrieve(self, query: str, collection: str, top_k: int = 5):
    """混合检索：向量 + 关键词"""
    # 1. 提取关键词
    keywords = self._extract_keywords(query)

    # 2. 向量检索（扩大范围）
    results = await self.retrieve(query, collection, top_k * 3)

    # 3. 关键词过滤/加权
    filtered = []
    for r in results:
        score = r.get("score", 0)
        text_lower = r.get("text", "").lower()
        keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if keyword_hits > 0:
            score += 0.1 * keyword_hits
        r["score"] = score
        filtered.append(r)

    # 4. 重排序
    filtered.sort(key=lambda x: x["score"], reverse=True)
    return filtered[:top_k]
```

#### 4. 异步任务队列

```python
# 建议引入 Redis 队列
# 添加解析进度查询接口
# 支持大文件批量处理
```

---

### 中优先级

#### 5. 解析进度实时反馈

```javascript
// 前端轮询解析状态
async function getParseStatus(kbId) {
    const res = await fetch(`${API_BASE}/api/report/knowledge/${kbId}/status`);
    return res.json();
}
```

#### 6. 错误处理和重试机制

```python
# 添加自动重试
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def process_with_retry(kb_id, file_content):
    ...
```

#### 7. 表格特殊处理

```
RAGFlow的表格处理:
- 表格结构识别 → 表头+行列
- 转为 markdown 格式
- 作为独立chunk存储
```

---

### 低优先级（高级功能）

#### 8. 知识图谱支持

```
RAGFlow GraphRAG:
- 实体抽取 (named entity recognition)
- 关系抽取 (relation extraction)
- 社区检测 (community detection)
- 社区报告生成
```

#### 9. 多租户隔离

```
当前aistock无租户概念
如需商用需增加 tenant_id 字段
```

#### 10. 引用溯源增强

```
RAGFlow的引用机制:
- chunk级别原文引用
- 直接引用 vs 间接引用区分
- 引用置信度评分
```

---

## 四、具体代码改动示例

### 改进1: 更好的分块策略

见上文"改进分块策略"代码示例。

### 改进2: 混合检索

见上文"添加混合检索"代码示例。

### 改进3: 解析进度追踪

**后端添加状态接口** (`report_analysis.py`):
```python
@router.get("/knowledge/{kb_id}/status")
async def get_knowledge_status(kb_id: str):
    """获取知识库解析状态"""
    try:
        mongodb = get_mongodb_service()
        kb = mongodb.get_knowledge(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="不存在")
        return {
            "success": True,
            "status": kb.get("status", "unknown"),
            "chunks_count": len(kb.get("chunks", [])),
            "vector_ids_count": len(kb.get("vector_ids", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**前端解析时显示进度**:
```javascript
async function parseKnowledge(kbId) {
    const btn = document.getElementById(`parseBtn_${kbId}`);
    const statusEl = document.getElementById(`parseStatus_${kbId}`);

    // 显示加载状态
    if (btn) { btn.disabled = true; btn.textContent = '解析中...'; }
    if (statusEl) {
        statusEl.style.display = 'inline';
        statusEl.textContent = '正在解析文件，请稍候...';
    }

    try {
        const res = await fetch(`${API_BASE}/api/report/knowledge/${kbId}/parse`, {
            method: 'POST'
        });
        const data = await res.json();

        if (data.success) {
            if (statusEl) statusEl.textContent = `✓ 解析完成，共 ${data.chunks_count} 个文本块`;
            setTimeout(() => loadKnowledge(), 1000);
        } else {
            if (btn) { btn.disabled = false; btn.textContent = '解析'; }
            if (statusEl) statusEl.style.display = 'none';
            alert('解析失败: ' + (data.detail || data.message || '未知错误'));
        }
    } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = '解析'; }
        if (statusEl) statusEl.style.display = 'none';
        alert('解析异常: ' + e.message);
    }
}
```

---

## 五、总结

| 方面 | aistock现状 | RAGFlow参考 | 改进建议 |
|------|------------|-------------|---------|
| 解析 | 基础文本提取 | 布局+OCR+表格识别 | 中期，引入DeepDOC |
| 分块 | 固定字符 | 多种策略 | **高优先级**，段落级分块 |
| 检索 | 纯向量 | 混合+重排 | **高优先级**，添加关键词匹配 |
| 存储 | ChromaDB | ES/Infinity | 中期，考虑迁移 |
| 任务 | asyncio | Redis队列 | 中期，添加任务队列 |
| 知识图谱 | 无 | GraphRAG | 长期目标 |

### 建议执行顺序

1. **第一阶段**（高优先级）：
   - 改进分块策略（保留段落/表格完整性）
   - 添加关键词匹配增强检索
   - 完善异步任务和进度追踪

2. **第二阶段**（中期）：
   - 增强文档解析能力（布局分析）
   - 考虑迁移到 ES/Infinity
   - 添加错误处理和重试机制

3. **第三阶段**（长期）：
   - 知识图谱支持
   - 多租户隔离
   - 高级引用溯源

---

## 六、相关文件路径

### aistock RAG 相关文件

| 文件 | 路径 | 用途 |
|------|------|------|
| `rag_service.py` | `backend/services/` | RAG核心服务 |
| `chroma_service.py` | `backend/services/` | 向量数据库操作 |
| `embedding_service.py` | `backend/services/` | Embedding生成 |
| `report_service.py` | `backend/services/` | 文档处理服务 |
| `report_analysis.py` | `backend/routers/` | REST API接口 |
| `chat_service.py` | `backend/services/` | 聊天服务 |

### RAGFlow 参考文件

| 目录 | 用途 |
|------|------|
| `/rag/app/` | 文档分块策略 |
| `/rag/nlp/` | NLP工具（检索、分词） |
| `/rag/nlp/search.py` | 混合检索实现 |
| `/rag/llm/` | LLM集成 |
| `/deepdoc/parser/` | 文档解析器 |
| `/rag/svr/task_executor.py` | 异步任务处理 |

---

*文档生成时间：2026-04-13*
