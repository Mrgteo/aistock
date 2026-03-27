# AI 股票交易辅助系统

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

一个基于 FastAPI 和原生前端的全栈股票分析系统，集成 DeepSeek AI 提供智能分析能力。本系统支持 A 股、港股、美股的实时技术分析、策略选股和交易复盘功能。

---

## 目录

- [项目概述](#项目概述)
- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [详细安装指南](#详细安装指南)
- [配置说明](#配置说明)
- [API 接口文档](#api-接口文档)
- [前端页面说明](#前端页面说明)
- [数据库设计](#数据库设计)
- [部署指南](#部署指南)
- [开发指南](#开发指南)
- [故障排除](#故障排除)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [许可证](#许可证)

---

## 项目概述

### 背景

随着量化投资和智能投顾的快速发展，个人投资者对股票分析工具的需求日益增长。本系统旨在为投资者提供一个**免费、易用、智能**的股票分析辅助平台，通过 AI 技术降低投资分析的门槛。

### 核心价值

| 价值主张 | 说明 |
|---------|------|
| 智能化 | 集成 DeepSeek AI，自动生成投资分析报告 |
| 全覆盖 | 支持 A 股、港股、美股三大主流市场 |
| 易用性 | 无需安装，浏览器即可使用 |
| 私密性 | 本地部署，数据完全自主可控 |

### 目标用户

- 散户投资者：缺乏专业分析工具的个人交易者
- 价值投资者：需要基本面与技术面结合分析的用户
- 短线交易者：需要实时技术指标和选股策略的用户
- 学习者：希望了解股票分析方法的初学者

---

## 功能特性

### 1. 用户系统

#### 1.1 认证功能
- **用户注册**：支持用户名、密码注册，自动分配默认角色
- **用户登录**：JWT Token 认证，支持 Token 自动续期
- **修改密码**：登录后可修改密码，需验证原密码
- **退出登录**：清除 Token，注销会话

#### 1.2 权限管理
| 角色 | 权限说明 |
|------|---------|
| 普通用户 | 使用分析、选股、复盘功能，管理个人数据 |
| 管理员 | 管理所有用户，查看系统状态，配置参数 |

#### 1.3 用户偏好
- 默认市场选择（A/港/美股）
- 界面主题（预留）
- 常用股票自选

### 2. 股票深度分析

#### 2.1 支持的市场

| 市场 | 代码格式 | 示例 | 数据源 |
|------|---------|------|--------|
| A股上证 | 6位数字 | 600000 | 腾讯财经 |
| A股深证 | 000xxx/300xxx | 000001/300001 | 腾讯财经 |
| 港股 | 4-5位数字.HK | 0700.HK | 腾讯财经 |
| 美股 | 英文代码 | AAPL/MSFT | 新浪财经 |

#### 2.2 技术指标

**均线系统 (MA)**
| 指标 | 说明 | 用途 |
|------|------|------|
| MA5 | 5日均线 | 短期趋势 |
| MA10 | 10日均线 | 短期趋势 |
| MA20 | 20日均线 | 中期趋势 |
| MA30 | 30日均线 | 中期趋势 |
| MA60 | 60日均线 | 长期趋势 |

**摆动指标**
| 指标 | 说明 | 交易信号 |
|------|------|---------|
| RSI(14) | 相对强弱指数 | >70超买，<30超卖 |
| MACD | 指数平滑异同移动平均线 | DIF上穿DEA金叉 |
| MACD Hist | MACD柱状图 | 红柱/绿柱动能 |

**价格通道**
| 指标 | 说明 |
|------|------|
| 52周高点 | 近一年最高价 |
| 52周低点 | 近一年最低价 |

#### 2.3 K线数据
- **日K线**：默认展示近6个月日K数据
- **数据字段**：日期、开、高、低、收、成交量
- **复权处理**：支持前复权和后复权

#### 2.4 AI 分析报告

系统自动生成结构化分析报告，包含：

```
📊 股票名称/代码 - AI 分析报告
━━━━━━━━━━━━━━━━━━━━━━

【技术面分析】
- 趋势判断：当前走势及均线排列
- 均线系统：MA5/10/20/30/60 分析
- MACD指标：DIF、DEA、柱状图解读
- RSI指标：当前值及超买/超卖判断
- 支撑压力：关键价位分析

【消息面分析】
- 近期重大公告（如有）
- 市场情绪评估

【基本面分析】（如有）
- 市盈率、市净率
- 行业地位
- 业绩概况

【风险提示】
- 技术面风险
- 市场风险
- 流动性风险

【投资建议】
- 短期操作建议
- 中长期趋势判断
- 仓位建议
```

### 3. 策略选股

#### 3.1 自然语言选股

支持类似自然语言的选股条件输入：

**支持的语法：**
| 语法示例 | 说明 |
|---------|------|
| `RSI14>70` | RSI14 大于 70 |
| `RSI14<30` | RSI14 小于 30 |
| `MA5>MA20` | 5日均线在20日均线上方 |
| `MACD>0` | MACD 在零轴上方 |
| `Price>100` | 股价大于100 |
| `RSI14>70; MA5>MA20` | 多条件组合（AND） |

#### 3.2 快捷策略

系统预设热门选股策略：

| 策略名称 | 条件 | 说明 |
|---------|------|------|
| 强势股 | MA5>MA20; RSI14>60 | 均线多头排列且RSI强势 |
| 超跌反弹 | RSI14<30 | RSI进入超卖区域 |
| MACD金叉 | DIF>DEA | MACD形成金叉信号 |
| 创阶段新高 | Price=52WHigh | 股价创52周新高 |
| 创阶段新低 | Price=52WLow | 股价创52周新低 |

#### 3.3 选股结果

返回匹配股票列表，每只股票包含：
- 股票代码和名称
- 当前价格
- 匹配的技术指标详情
- 入选理由说明
- AI 初步评估

### 4. 交易复盘

#### 4.1 日历复盘

- **日历界面**：直观选择历史日期
- **日期导航**：支持快速切换月份
- **复盘状态**：已复盘日期标记

#### 4.2 复盘内容

| 字段 | 说明 | 必填 |
|------|------|------|
| 今日总结 | 当日交易心得 | 是 |
| 明日计划 | 次日交易计划 | 是 |
| 持仓情况 | 当前持仓及盈亏 | 否 |
| 经验教训 | 交易中的反思 | 否 |

#### 4.3 图片上传

- 支持上传交易截图（PNG/JPG，最大5MB）
- 自动关联到对应复盘日期
- 存储在本地 `uploads/` 目录

#### 4.4 AI 复盘分析

基于复盘内容，AI 自动分析：
- 盈亏情况评估
- 交易偏离度分析
- 操作纪律遵守情况
- 改进建议

### 5. 市场行情

#### 5.1 全球股指概览

| 功能 | 说明 | 数据源 |
|------|------|--------|
| A股常用指数 | 上证、深证、创业板、沪深300、上证50 | 腾讯财经 |
| 港股指数 | 恒生、恒生科技、国企指数 | 腾讯财经 |
| 美股指数 | 道琼斯、纳斯达克、标普500 | Yahoo Finance |
| 欧洲指数 | 伦敦、法兰克福、巴黎等 | 腾讯财经 |
| 亚洲指数 | 东京、首尔、台湾等 | 腾讯财经 |

#### 5.2 实时新闻

| 功能 | 说明 | 数据源 |
|------|------|--------|
| 财联社电报 | 实时财经快讯，30秒自动刷新 | 财联社 |
| 同花顺新闻 | 财经新闻列表，支持分页加载 | 同花顺 |

#### 5.3 市场状态

系统根据北京时间自动判断各市场状态：
- **A股**：交易时间 9:15-15:00
- **港股**：交易时间 9:00-16:00
- **美股**：交易时间 21:30-次日04:00

### 6. AI研报分析

#### 6.1 研报管理

- **上传研报**：支持 PDF、DOCX、DOC、TXT 格式
- **研报列表**：分页浏览，管理已上传研报
- **研报删除**：删除研报及关联向量数据

#### 6.2 RAG 智能分析

基于检索增强生成（RAG）技术，实现对研报内容的深度理解：

```
用户上传研报 → 文档解析 → 文本分块(512字符) → 向量化存储(ChromaDB)
                                                              ↓
用户提问    → 语义检索(Top-K) → 上下文构建 → DeepSeek LLM → AI回答
```

#### 6.3 知识库

- 上传补充知识库文件
- 语义检索知识库内容
- 支持标签分类管理

#### 6.4 分析历史

- 保存每次分析的问答记录
- 查看分析详情和参考来源
- 管理分析历史

### 7. 系统设置

#### 7.1 账户设置
- 修改登录密码
- 更换绑定邮箱
- 查看账户信息

#### 7.2 界面偏好

| 功能 | 选项 |
|------|------|
| 主题模式 | 浅色 / 深色 |
| 默认市场 | A股 / 港股 / 美股 |
| K线深度 | 3个月 / 6个月 / 12个月 |

#### 7.3 自动刷新

- 行情自动刷新开关
- 可配置刷新间隔（30秒/60秒/120秒）

#### 7.4 通知设置

- 系统通知开关
- 重要新闻提醒（红色标记）

---

## 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              原生 HTML/CSS/JavaScript               │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │   │
│  │  │ 登录页 │ │ 分析页 │ │ 选股页 │ │ 复盘页 │      │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘      │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐                 │   │
│  │  │ 市场页 │ │ 研报页 │ │ 设置页 │                 │   │
│  │  └────────┘ └────────┘ └────────┘                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Nginx 反向代理                          │
│                      (可选，Docker部署)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    前端静态文件服务器                        │
│                     Python HTTP Server                      │
│                        Port: 3017                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端服务                          │
│                      Port: 8000                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    API Routes                        │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │  │
│  │  │  Auth   │ │  Stock  │ │Analysis │ │ Review  │    │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │  │
│  │  │ Market  │ │ Report  │ │History  │ │Screener │    │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Services Layer                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ AuthService │  │StockService │  │AI Service   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │RAG Service │  │MongoDB     │  │ChromaDB    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│   SQLite    │    │   外部数据源     │    │  DeepSeek   │
│  用户数据    │    │  腾讯/新浪/东财  │    │    AI API   │
└─────────────┘    └─────────────────┘    └─────────────┘
```

### 技术栈详情

#### 后端技术

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | FastAPI | 0.110+ | 高性能异步 API 框架 |
| 服务器 | Uvicorn | 最新 | ASGI 服务器 |
| 数据验证 | Pydantic | 2.0+ | 数据模型和验证 |
| 数据处理 | Pandas | 最新 | 数据分析处理 |
| 数据库 | SQLite | 3.x | 轻量级关系数据库 |
| 文档数据库 | MongoDB | 最新 | 研报数据存储 |
| 向量数据库 | ChromaDB | 最新 | RAG 向量存储 |
| JWT | python-jose | 最新 | Token 生成和验证 |
| 密码加密 | passlib | 最新 | Bcrypt 密码哈希 |

#### 前端技术

| 组件 | 技术 | 说明 |
|------|------|------|
| 结构 | HTML5 | 语义化标签 |
| 样式 | CSS3 | 原生 CSS，支持响应式 |
| 交互 | JavaScript ES6+ | 原生 JS，无框架依赖 |
| 图表 | ECharts | 股票K线图表渲染 |
| 图表 | 无外部依赖 | 直接使用原生 Canvas |

#### 外部服务

| 服务 | 提供商 | 用途 |
|------|--------|------|
| 股票数据 | 腾讯财经 | A股、港股实时数据 |
| 股票数据 | 新浪财经 | 美股数据 |
| 股票数据 | 东方财富 | 基本面数据 |
| AI 分析 | DeepSeek | GPT 类型对话服务 |

---

## 项目结构

```
stock_trade/
├── backend/                        # 后端目录
│   ├── __init__.py
│   ├── app.py                      # FastAPI 应用入口
│   ├── main.py                     # 主模块（别名）
│   ├── requirements.txt            # Python 依赖
│   ├── core/                       # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py               # 配置管理
│   │   ├── database.py             # 数据库连接
│   │   ├── security.py             # 安全工具（JWT等）
│   │   └── deps.py                 # 依赖注入
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py                 # 用户模型
│   │   └── review.py                # 复盘模型
│   ├── routers/                    # 路由模块
│   │   ├── __init__.py
│   │   ├── auth.py                 # 认证路由
│   │   ├── stock.py                # 股票数据路由
│   │   ├── analysis.py             # 分析路由
│   │   └── review.py               # 复盘路由
│   ├── services/                   # 服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py          # 认证服务
│   │   ├── user_service.py         # 用户服务
│   │   ├── stock_service.py        # 股票数据服务
│   │   └── ai_service.py           # AI 分析服务
│   ├── data/                       # 复盘数据存储
│   │   └── reviews/               # JSON 格式复盘文件
│   └── uploads/                   # 上传文件存储
│       └── images/                # 复盘截图
├── frontend/                       # 前端目录
│   ├── index.html                  # 主页面（框架）
│   ├── login.html                  # 登录/注册页面
│   ├── register.html               # 注册页面（可选）
│   ├── analyze.html                # 股票分析页面
│   ├── shortlist.html              # 策略选股页面
│   ├── review.html                 # 交易复盘页面
│   ├── css/                        # 样式目录
│   │   └── style.css               # 主样式文件
│   └── js/                         # 脚本目录
│       ├── api.js                  # API 调用封装
│       ├── auth.js                 # 认证逻辑
│       ├── analyze.js              # 分析页面逻辑
│       ├── shortlist.js            # 选股页面逻辑
│       └── review.js               # 复盘页面逻辑
├── frontend_server.py             # 前端服务器
├── docker-compose.yml             # Docker 编排配置
├── Dockerfile                     # 后端镜像构建
├── nginx.conf                     # Nginx 配置
├── .env                           # 环境变量（需创建）
├── .env.example                   # 环境变量示例
├── stock_trade.db                 # SQLite 数据库文件
├── data/                          # 数据目录
│   └── reviews/                   # 复盘数据（JSON）
├── docs/                          # 文档目录
│   └── api.md                     # API 文档
├── README.md                      # 项目说明
└── LICENSE                        # 许可证
```

---

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd stock_trade

# 2. 复制环境配置文件
cp .env.example .env

# 3. 编辑 .env 文件，填入 DeepSeek API Key
nano .env

# 4. 启动服务
docker-compose up -d

# 5. 访问系统
open http://localhost
```

### 方式二：本地运行

```bash
# 1. 进入项目目录
cd stock_trade

# 2. 创建并激活 conda 环境
conda create -n stock python=3.10
conda activate stock

# 3. 安装后端依赖
cd backend
pip install -r requirements.txt

# 4. 复制并编辑配置文件
cp ../.env.example ../.env
nano ../.env

# 5. 返回项目根目录，启动后端
cd ..
python -m backend.app &

# 6. 启动前端服务器
python frontend_server.py &

# 7. 访问系统
open http://localhost:3017
```

### 方式三：直接运行（用于开发）

```bash
# 激活环境
conda activate stock

# 启动后端（热重载模式）
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 新终端 - 启动前端
cd frontend_server
python frontend_server.py
```

---

## 详细安装指南

### 环境要求

| 要求 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.8 | 3.10/3.11 |
| conda | 4.12 | 最新版 |
| Docker | 20.10 | 24.0 |
| Docker Compose | 2.0 | 2.20+ |
| 内存 | 4GB | 8GB+ |
| 硬盘 | 2GB | 10GB+ |

### Windows WSL2 环境

```bash
# 1. 安装 WSL2（PowerShell 管理员）
wsl --install

# 2. 安装 Ubuntu
wsl --install -d Ubuntu

# 3. 安装 Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 4. 创建环境
conda create -n stock python=3.10
conda activate stock

# 5. 安装 Git 和项目依赖
sudo apt update
sudo apt install git
git clone <repo-url>
cd stock_trade
```

### macOS 环境

```bash
# 1. 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装 Miniconda
brew install miniconda
conda init zsh

# 3. 创建环境
conda create -n stock python=3.10
conda activate stock

# 4. 安装项目
git clone <repo-url>
cd stock_trade
cd backend && pip install -r requirements.txt
```

### Docker 部署详解

#### docker-compose.yml 配置说明

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./uploads:/app/uploads
      - ./data:/app/data
      - ./stock_trade.db:/app/stock_trade.db
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - backend
    restart: unless-stopped
```

#### 自定义 Nginx 配置

如需修改端口或添加 HTTPS，可编辑 `nginx.conf`。

### 前端服务器配置

前端服务器使用 Python 内置 HTTP 服务器：

| 配置项 | 默认值 | 说明 |
|--------|-------|------|
| PORT | 3017 | 前端服务端口 |
| FRONTEND_DIR | ./frontend | 前端文件目录 |
| API_PORT | 8017 | API 代理端口 |

如需修改，编辑 `frontend_server.py` 中的配置常量。

---

## 配置说明

### 配置文件优先级

配置按以下优先级生效（高 → 低）：
1. 环境变量
2. `.env` 文件
3. `config.py` 默认值

### .env 文件配置

```bash
# =============================================
# DeepSeek API 配置（必需）
# =============================================
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEFAULT_MODEL_NAME=deepseek-chat

# =============================================
# JWT 安全配置（生产环境必须修改）
# =============================================
JWT_SECRET=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24小时

# =============================================
# 服务器配置
# =============================================
HOST=0.0.0.0
PORT=8000
DEBUG=true

# =============================================
# 数据库配置
# =============================================
DB_PATH=stock_trade.db

# =============================================
# 文件上传配置
# =============================================
UPLOAD_DIR=backend/uploads
MAX_UPLOAD_SIZE=5242880  # 5MB

# =============================================
# 股票数据源配置
# =============================================
# 备用数据源（逗号分隔）
STOCK_DATA_SOURCES=tencent,sina,eastmoney
```

### DeepSeek API Key 获取

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册/登录账号
3. 进入「API Keys」页面
4. 创建新的 API Key
5. 复制并填入 `.env` 文件

### 配置验证

启动前可验证配置是否正确：

```python
# 在 backend 目录下执行
python -c "from core.config import settings; print(settings.model_dump())"
```

---

## API 接口文档

### 基础信息

| 项目 | 说明 |
|------|------|
| Base URL | `http://localhost:8000` |
| API 文档 | `http://localhost:8000/docs` |
| 健康检查 | `http://localhost:8000/health` |

### 认证说明

除公开接口外，所有 API 请求需要在 Header 中携带 Token：

```
Authorization: Bearer <your-jwt-token>
```

### 认证接口

#### POST /api/auth/register

注册新用户。

**请求参数：**
```json
{
  "username": "string",    // 用户名，3-20字符
  "password": "string",    // 密码，6-20字符
  "email": "string"        // 邮箱（可选）
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "注册成功",
  "data": {
    "id": 1,
    "username": "testuser",
    "role": "user"
  }
}
```

#### POST /api/auth/login

用户登录。

**请求参数：**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

#### GET /api/auth/me

获取当前用户信息。

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "username": "admin",
    "email": null,
    "role": "admin",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

#### POST /api/auth/change-password

修改密码。

**请求参数：**
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

#### GET /api/auth/users

获取用户列表（仅管理员）。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码（默认1） |
| page_size | int | 每页数量（默认10） |

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 10,
    "users": [...]
  }
}
```

### 股票接口

#### GET /api/stock/kline

获取 K 线数据。

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 股票代码 |
| market | string | 否 | 市场（A/H/US，默认自动识别） |
| period | string | 否 | 周期（day/week/month，默认day） |
| adjust | string | 否 | 复权类型（qfq/qsb/qsbfq，默认qfq） |

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "code": "600000",
    "name": "浦发银行",
    "market": "A",
    "klines": [
      {
        "date": "2024-01-02",
        "open": 10.50,
        "high": 10.80,
        "low": 10.45,
        "close": 10.75,
        "volume": 12345678
      }
    ]
  }
}
```

#### GET /api/metrics

获取股票技术指标。

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 股票代码 |
| market | string | 否 | 市场 |

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "code": "600000",
    "name": "浦发银行",
    "price": 10.75,
    "change": 0.25,
    "change_pct": 2.38,
    "ma": {
      "MA5": 10.65,
      "MA10": 10.58,
      "MA20": 10.50,
      "MA30": 10.45,
      "MA60": 10.40
    },
    "rsi": {
      "RSI6": 65.5,
      "RSI12": 62.3,
      "RSI24": 58.7
    },
    "macd": {
      "DIF": 0.15,
      "DEA": 0.12,
      "HIST": 0.03
    },
    "high_52w": 11.50,
    "low_52w": 9.20
  }
}
```

#### GET /api/stock/news

获取股票新闻。

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 股票代码 |

**响应示例：**
```json
{
  "code": 200,
  "data": [
    {
      "title": "浦发银行发布2023年年报",
      "source": "东方财富",
      "date": "2024-03-25",
      "url": "https://..."
    }
  ]
}
```

#### GET /api/stock/fundamental

获取股票基本面数据。

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 股票代码 |

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "code": "600000",
    "name": "浦发银行",
    "pe": 5.2,
    "pb": 0.65,
    "market_cap": 35000000000,
    "dividend_yield": 4.5,
    "revenue": 180000000000,
    "profit": 5500000000
  }
}
```

### 分析接口

#### POST /api/chat

AI 对话/分析。

**请求参数：**
```json
{
  "message": "分析一下贵州茅台的走势",
  "code": "600519"  // 可选，关联股票代码
}
```

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "reply": "【贵州茅台 600519 技术分析】\n\n【技术面】...",
    "code": "600519",
    "model": "deepseek-chat"
  }
}
```

#### GET /api/hot_strategies

获取热门选股策略。

**响应示例：**
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "强势股",
      "description": "均线多头排列",
      "conditions": "MA5>MA20;RSI14>60",
      "tags": ["趋势", "短线"]
    }
  ]
}
```

#### POST /api/simple_screen

执行选股筛选。

**请求参数：**
```json
{
  "conditions": "RSI14>70;MA5>MA20",
  "market": "A"  // 可选：A/H/US/AUTO
}
```

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "total": 5,
    "stocks": [
      {
        "code": "600519",
        "name": "贵州茅台",
        "price": 1680.00,
        "change_pct": 3.25,
        "matched_conditions": {
          "RSI14": 75.5,
          "MA5": 1650,
          "MA20": 1600
        },
        "reason": "RSI进入超买区域但均线多头排列明显..."
      }
    ]
  }
}
```

### 复盘接口

#### GET /api/review/{date}

获取指定日期的复盘记录。

**路径参数：**
| 参数 | 格式 | 说明 |
|------|------|------|
| date | YYYY-MM-DD | 日期 |

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "date": "2024-03-25",
    "summary": "今日操作一般...",
    "plan": "明日关注科技股机会",
    "positions": "持有3成仓",
    "lessons": "追高容易亏损",
    "images": ["/uploads/images/2024-03-25_1.png"],
    "ai_analysis": null,
    "created_at": "2024-03-25T18:00:00",
    "updated_at": "2024-03-25T18:30:00"
  }
}
```

#### POST /api/review/{date}

保存复盘记录。

**请求参数：**
```json
{
  "summary": "今日总结内容",
  "plan": "明日计划内容",
  "positions": "持仓情况（可选）",
  "lessons": "经验教训（可选）"
}
```

#### POST /api/review/upload/{date}

上传复盘图片。

**请求格式：** `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 图片文件（PNG/JPG，最大5MB） |

**响应示例：**
```json
{
  "code": 200,
  "msg": "上传成功",
  "data": {
    "url": "/uploads/images/2024-03-25_1.png"
  }
}
```

#### POST /api/review/ai_analyze

AI 复盘分析。

**请求参数：**
```json
{
  "date": "2024-03-25"
}
```

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "date": "2024-03-25",
    "analysis": "【AI 复盘分析】\n\n【盈亏评估】...\n【偏离度分析】...\n【改进建议】...",
    "score": 75
  }
}
```

### 市场接口

#### GET /api/market/global_indices

获取全球股指数据。

**响应示例：**
```json
{
  "common": [
    {"name": "上证指数", "code": "sh000001", "price": "3200.00", "change": 0.65, "state": "open"}
  ],
  "cn": [...],
  "hk": [...],
  "us": [...],
  "europe": [...],
  "asia": [...]
}
```

#### GET /api/market/telegraph

获取实时新闻电报。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| source | string | 数据源：cls=财联社，ths=同花顺 |
| page | int | 页码（仅同花顺） |

### 研报接口

#### POST /api/report/upload

上传研报文件。

**请求格式：** `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 研报文件（PDF/DOCX/DOC/TXT） |
| title | string | 研报标题 |
| report_type | string | 研报类型 |
| industry | string | 所属行业 |

#### POST /api/report/analyze

AI 分析研报内容。

**请求参数：**
```json
{
  "report_id": "uuid",
  "query": "新能源汽车市场未来趋势如何？",
  "use_knowledge_base": true,
  "top_k": 5
}
```

**响应示例：**
```json
{
  "success": true,
  "analysis_id": "uuid",
  "ai_analysis": "根据该研报分析...",
  "sources": [
    {"chunk_index": 0, "content": "..."}
  ]
}
```

### 历史接口

#### GET /api/history/records

获取历史分析记录列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| limit | int | 返回数量（默认50） |
| offset | int | 偏移量（默认0） |

---

## 前端页面说明

### 页面结构

```
┌──────────────────────────────────────────────────────────┐
│                      顶部导航栏                          │
│  Logo   |   首页   |   关于   |        用户名   退出      │
├─────────┬────────────────────────────────────────────────┤
│         │                                                │
│  侧边   │                                                │
│  导航   │              主内容区域                         │
│         │                                                │
│  ○ 分析 │           (iframe 加载各子页面)                 │
│  ○ 选股 │                                                │
│  ○ 复盘 │                                                │
│  ○ 市场 │                                                │
│  ○ 研报 │                                                │
│         │                                                │
├─────────┴────────────────────────────────────────────────┤
│                      底部版权                            │
└──────────────────────────────────────────────────────────┘
```

### 页面详情

#### 1. 登录页面 (login.html)

**功能：**
- 用户登录表单
- 注册入口
- 表单验证
- 错误提示

**交互逻辑：**
1. 用户输入用户名密码
2. 点击登录，调用 `/api/auth/login`
3. 成功：存储 Token，跳转主页
4. 失败：显示错误信息

#### 2. 股票分析页面 (analyze.html)

**功能：**
- 股票代码输入
- 市场选择（A/港/美股）
- K 线图表展示
- 技术指标面板
- AI 分析报告生成

**图表说明：**
- K 线图（蜡烛图）
- 均线叠加
- 成交量柱状图
- MACD 副图

**操作流程：**
1. 输入股票代码
2. 选择市场（自动识别可省略）
3. 点击「分析」
4. 查看 K 线和技术指标
5. 点击「AI 分析」获取报告

#### 3. 策略选股页面 (shortlist.html)

**功能：**
- 选股条件输入框
- 快捷策略标签
- 选股结果列表
- 股票详情弹窗

**选股语法：**
- 单条件：`RSI14>70`
- 多条件：`RSI14>70;MA5>MA20`
- 支持比较符：`>` `<` `=` `>=` `<=`

#### 4. 交易复盘页面 (review.html)

**功能：**
- 日历选择器
- 复盘表单编辑
- 图片上传
- AI 复盘分析
- 历史复盘查看

**日历交互：**
- 点击日期查看/编辑复盘
- 有复盘的日期标记圆点
- 支持月份切换

#### 5. 市场行情页面 (market.html)

**功能：**
- 标签页切换（A股/港股/美股/欧股/亚股）
- 全球股指概览展示
- 实时新闻电报（财联社）
- 同花顺新闻分页加载
- 刷新按钮手动更新

**数据展示：**
- A股常用5大指数（上证/深证/创业板/沪深300/上证50）
- 涨跌额和涨跌幅颜色标识
- 市场状态标识（开市/闭市）

#### 6. AI研报分析页面 (report_analysis.html)

**功能：**
- 左侧导航（研报列表/上传/知识库/分析历史）
- 研报上传（支持PDF/DOCX/DOC/TXT）
- RAG智能问答分析
- 研报中提及的股票/行业提取
- 分析历史记录管理

**分析流程：**
1. 选择或上传研报
2. 输入问题
3. 点击分析
4. 查看AI回答和参考来源

#### 7. 系统设置页面 (settings.html)

**功能：**
- 左侧导航（账户/界面/刷新/通知）
- 账户设置（修改密码）
- 界面偏好（主题/默认市场/K线深度）
- 自动刷新配置
- 通知设置

**主题切换：**
- 浅色主题 / 深色主题
- 实时预览效果

---

## 数据库设计

### 数据库文件

- **用户数据**：`stock_trade.db`（SQLite）
- **复盘数据**：`data/reviews/*.json`
- **研报数据**：MongoDB
- **向量索引**：ChromaDB
- **上传文件**：`backend/uploads/*`

### 用户表 (users)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',  -- user, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
```

### 复盘数据 (JSON)

```json
{
  "date": "2024-03-25",
  "user_id": 1,
  "summary": "复盘内容",
  "plan": "明日计划",
  "positions": "持仓情况",
  "lessons": "经验教训",
  "images": ["image1.png", "image2.png"],
  "ai_analysis": "AI分析结果",
  "ai_score": 85,
  "created_at": "2024-03-25T18:00:00",
  "updated_at": "2024-03-25T18:30:00"
}
```

---

## 部署指南

### 开发环境部署

```bash
# 1. 克隆代码
git clone <repo-url>
cd stock_trade

# 2. 创建环境
conda create -n stock python=3.10
conda activate stock

# 3. 安装依赖
cd backend && pip install -r requirements.txt

# 4. 配置
cp .env.example .env
# 编辑 .env 填入 API Key

# 5. 启动
python -m backend.app &        # 后端
python frontend_server.py &    # 前端
```

### 生产环境 Docker 部署

```bash
# 1. 服务器配置 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. 部署项目
git clone <repo-url>
cd stock_trade
cp .env.example .env
nano .env  # 配置必填项

# 4. 启动服务
docker-compose up -d --build

# 5. 检查状态
docker-compose ps
docker-compose logs -f
```

### Nginx 反向代理配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/stock_trade/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # 上传文件
    location /uploads {
        alias /var/www/stock_trade/backend/uploads;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

### HTTPS 配置

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 系统服务配置 (systemd)

创建 `/etc/systemd/system/stock-trade.service`：

```ini
[Unit]
Description=Stock Trade AI System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/stock_trade
ExecStart=/opt/miniconda3/envs/stock/bin/python -m backend.app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl enable stock-trade
sudo systemctl start stock-trade
sudo systemctl status stock-trade
```

---

## 开发指南

### 项目开发环境搭建

```bash
# 1. 克隆项目
git clone <repo-url>
cd stock_trade

# 2. 创建开发环境
conda create -n stock python=3.10
conda activate stock

# 3. 安装依赖
cd backend
pip install -r requirements.txt

# 4. 安装预提交钩子
pip install pre-commit
pre-commit install

# 5. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 代码规范

#### Python 代码规范

- 遵循 PEP 8
- 使用类型注解
- 文档字符串使用 Google 风格

```python
def get_stock_metrics(code: str, market: str = "A") -> dict:
    """获取股票技术指标

    Args:
        code: 股票代码
        market: 市场类型，默认A股

    Returns:
        包含技术指标的字典

    Raises:
        ValueError: 无效的股票代码
    """
    pass
```

#### 前端代码规范

- 使用 ES6+ 语法
- 变量命名使用 camelCase
- 常量使用 UPPER_SNAKE_CASE
- 注释使用 JSDoc 风格

### 添加新功能

#### 1. 添加新的 API 路由

```python
# backend/routers/new_feature.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.deps import get_current_user

router = APIRouter(prefix="/api/new_feature", tags=["新功能"])

class NewFeatureRequest(BaseModel):
    param: str

@router.post("/action")
async def new_action(
    req: NewFeatureRequest,
    current_user = Depends(get_current_user)
):
    return {"code": 200, "data": {"result": "success"}}
```

#### 2. 注册路由

```python
# backend/app.py
from routers import new_feature

app.include_router(new_feature.router)
```

#### 3. 添加前端页面

```html
<!-- frontend/new_feature.html -->
<!DOCTYPE html>
<html>
<head>
    <title>新功能</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <!-- 页面内容 -->
    <script src="js/new_feature.js"></script>
</body>
</html>
```

### 测试

```bash
# 运行所有测试
pytest

# 运行指定测试
pytest tests/test_stock.py -v

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

---

## 故障排除

### 常见问题

#### 1. 启动报错 "ModuleNotFoundError"

**原因：** 依赖未安装

**解决：**
```bash
pip install -r backend/requirements.txt
```

#### 2. 数据库报错 "SQLite table is locked"

**原因：** 多进程访问 SQLite

**解决：**
- 开发环境：确保只有一个进程访问数据库
- 改用 PostgreSQL/MySQL（生产环境）

#### 3. AI 接口超时

**原因：** DeepSeek API 响应慢或网络问题

**解决：**
- 检查 API Key 是否正确
- 检查网络连接
- 增加超时时间配置

#### 4. 股票数据获取失败

**原因：** 数据源反爬或网络问题

**解决：**
```bash
# 检查数据源配置
# 尝试备用数据源
STOCK_DATA_SOURCES=sina,tencent,eastmoney
```

#### 5. 前端无法访问 API

**原因：** CORS 跨域问题

**解决：**
- 开发环境：后端已配置 CORS
- 生产环境：使用 Nginx 代理

#### 6. 图片上传失败

**原因：** 目录权限或文件大小超限

**解决：**
```bash
# 设置上传目录权限
chmod 755 backend/uploads
chmod 755 backend/uploads/images

# 检查文件大小（默认5MB）
```

#### 7. Docker 容器内存不足

**解决：**
```bash
# 增加 Docker 内存限制
# Docker Desktop -> Settings -> Resources -> Memory: 4GB+
```

### 日志查看

```bash
# 后端日志
tail -f backend/app.log

# Docker 日志
docker-compose logs -f backend

# Nginx 日志
tail -f /var/log/nginx/error.log
```

### 调试模式

```bash
# 启用调试模式
export DEBUG=true

# 或在 .env 中设置
DEBUG=true
```

---

## 常见问题

### Q: 如何获取 DeepSeek API Key？

A: 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)，注册账号后在 API Keys 页面创建。

### Q: 系统支持哪些股票市场？

A: 支持A股（600xxx、000xxx、300xxx）、港股（xxxx.HK）、美股（英文代码如AAPL）。

### Q: 数据多久更新一次？

A: 股票K线数据实时获取，技术指标根据实时数据计算。建议每次分析前刷新数据。

### Q: 我的数据存储在哪里？

A: 用户数据存储在 `stock_trade.db`，复盘数据存储在 `data/reviews/*.json`，图片存储在 `backend/uploads/images/`。

### Q: 如何修改默认管理员密码？

A: 登录后访问个人中心，或使用 API：`POST /api/auth/change-password`

### Q: 可以自定义选股策略吗？

A: 可以。在选股页面使用自然语言条件语法，如 `RSI14>70;MA5>MA20`。

### Q: AI 分析准确吗？

A: AI 分析仅供参考，不构成投资建议。投资有风险，决策需谨慎。

### Q: 如何备份数据？

```bash
# 备份数据库
cp stock_trade.db stock_trade.db.backup

# 备份复盘数据
tar -czf reviews_backup.tar.gz data/reviews/

# 备份上传文件
tar -czf uploads_backup.tar.gz backend/uploads/
```

### Q: 如何升级版本？

```bash
# 拉取最新代码
git pull origin main

# 重新构建
docker-compose build

# 重启服务
docker-compose up -d
```

---

## 更新日志

### v1.0.0 (2024-xx-xx)

- 实现用户认证系统
- 实现股票K线和技术指标获取
- 实现AI智能分析功能
- 实现策略选股功能
- 实现交易复盘功能
- 支持Docker部署

### 计划功能

- [ ] 添加布林带、KDJ等技术指标
- [ ] 支持更多国际市场
- [ ] 移动端适配
- [ ] Redis缓存支持
- [ ] PostgreSQL数据库支持
- [ ] 微信/邮件通知
- [ ] 量化交易接口对接

---

## 许可证

本项目基于 MIT 许可证开源。

---

## 联系方式

- 项目主页：https://github.com/yourusername/stock_trade
- 问题反馈：https://github.com/yourusername/stock_trade/issues
- 讨论交流：https://github.com/yourusername/stock_trade/discussions

---

*最后更新：2024-03-26*
