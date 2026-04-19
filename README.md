# AIStock - 智能股票交易辅助系统

基于 AI 的智能股票分析交易辅助系统，支持市场行情监控、AI 股票分析、龙虎榜分析、量化选股、交易复盘等功能。

## 功能模块

### 1. 市场行情
- 全球指数实时行情（A股、港股、美股、欧洲、亚洲）
- 市场快讯（财联社、同花顺）
- AI 新闻舆情分析助手

### 2. AI 股票分析
- 多分析师团队：技术分析、基本面分析、资金面分析、风险分析、情绪分析
- AI 综合讨论与投资决策
- 历史分析记录查询

### 3. 龙虎榜分析
- 营业部/游资追踪
- AI 智能评分系统
- 主力资金流向分析
- 推荐个股跟踪

### 4. 量化选股
- 自然语言智能选股（同花顺问财）
- 热门策略精选
- 五大量化策略：
  - 主力资金策略
  - 低价牛股策略
  - 小盘成长策略
  - 业绩增长策略
  - 低估值策略

### 5. 交易复盘
- 日历式复盘
- 交易记录管理
- AI 复盘分析

### 6. 研报分析
- PDF 研报上传与管理
- RAG 智能问答
- 知识库管理
- 问答会话记录

### 7. 系统设置
- 大模型配置（DeepSeek）
- 阿里云 DashScope 配置（Embedding/Rerank）
- PaddleOCR 配置
- 数据源配置
- 缓存管理

## 技术架构

### 后端
- **框架**：FastAPI
- **AI 模型**：DeepSeek API
- **向量数据库**：Chroma
- **缓存**：Redis
- **数据库**：SQLite + MongoDB

### 前端
- 纯静态 HTML/CSS/JavaScript
- 无需构建工具

### 部署
- Docker Compose 一键部署
- Nginx 反向代理

## 项目结构

```
aistock/
├── backend/
│   ├── app.py                 # FastAPI 主应用
│   ├── core/                  # 核心模块
│   │   ├── config.py          # 配置管理
│   │   ├── responses.py       # 响应封装
│   │   └── logging.py         # 日志配置
│   ├── routers/               # API 路由
│   │   ├── auth.py           # 认证接口
│   │   ├── stock.py          # 股票数据
│   │   ├── analysis.py       # AI 分析
│   │   ├── market.py         # 市场行情
│   │   ├── screener.py       # 智能选股
│   │   ├── longhubang.py     # 龙虎榜
│   │   ├── custom_strategy.py # 量化策略
│   │   ├── review.py         # 交易复盘
│   │   ├── report_analysis.py # 研报分析
│   │   ├── history.py        # 历史记录
│   │   └── settings.py       # 系统设置
│   └── services/             # 业务服务
│       ├── llm_service.py    # DeepSeek API
│       ├── rag_service.py    # RAG 服务
│       ├── embedding_service.py   # 向量化
│       ├── rerank_service.py     # 重排序
│       ├── chroma_service.py      # 向量数据库
│       ├── redis_service.py       # Redis 缓存
│       ├── mongodb_service.py     # MongoDB
│       ├── paddleocr_service.py   # OCR 服务
│       └── longhubang_*.py       # 龙虎榜相关
├── frontend/
│   ├── index.html            # 主面板
│   ├── login.html            # 登录注册
│   ├── market.html           # 市场行情
│   ├── analyze.html          # AI 分析
│   ├── shortlist.html        # 智能选股
│   ├── longhubang.html       # 龙虎榜
│   ├── custom_strategy.html   # 量化策略
│   ├── review.html           # 交易复盘
│   ├── report_analysis.html   # 研报分析
│   └── settings.html         # 系统设置
├── database/
│   └── chroma/              # Chroma 向量库
├── docker-compose.yml        # Docker 部署
├── Dockerfile               # 后端容器
└── nginx.conf              # Nginx 配置
```

## 快速开始

### 环境要求
- Python 3.9+
- Redis
- MongoDB
- Chroma

### 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

主要配置项：
- `DEEPSEEK_API_KEY` - DeepSeek API 密钥
- `DASHSCOPE_API_KEY` - 阿里云 DashScope API 密钥
- `MONGODB_URL` - MongoDB 连接地址
- `REDIS_URL` - Redis 连接地址

### 启动服务

**开发环境：**

```bash
# 启动后端 (端口 8017)
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8017 --reload

# 新开终端启动前端服务器 (端口 3017)
python frontend_server.py
```

**Docker 部署：**

```bash
docker-compose up -d
```

访问 `http://localhost:3017` 即可使用。

## API 接口

### 认证接口 `/api/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /login | 用户登录 |
| POST | /register | 用户注册 |
| GET | /me | 获取当前用户 |

### 市场接口 `/api/market`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /global_indices | 全球指数 |
| GET | /telegraph | 市场快讯 |
| POST | /news-analysis | AI 新闻分析 |

### 分析接口 `/api`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /analysis/single | 单股深度分析 |
| POST | /chat | AI 对话/分析 |

### 龙虎榜接口 `/api/longhubang`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /analyze | 运行龙虎榜分析 |
| GET | /reports | 历史报告 |
| GET | /top/youzi | 游资排名 |
| GET | /top/stocks | 活跃个股 |

### 研报接口 `/api/report`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /upload | 上传研报 |
| POST | /analyze | RAG 分析 |
| POST | /knowledge/search | 知识库搜索 |

### 设置接口 `/api/settings`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /llm | 获取 LLM 配置 |
| POST | /llm/test | 测试 LLM 连接 |
| POST | /llm/embedding/test | 测试 Embedding |
| GET | /cache/status | 缓存状态 |
| POST | /cache/clear | 清理缓存 |

## 数据库

| 数据库 | 路径 | 用途 |
|--------|------|------|
| stock_trade.db | 根目录 | 用户认证、系统设置 |
| stock_analysis.db | 根目录 | 股票分析历史记录 |
| longhubang.db | 根目录 | 龙虎榜数据 |

## License

MIT License
