# 智能简历解析与流式问答助手 POC 设计文档

> 创建日期: 2026-01-02
> 状态: 已确认

---

## 1. 项目概述

### 1.1 需求背景

构建一个集成**智能简历解析**和**流式卡片问答**的统一系统，用于POC验证。

### 1.2 核心功能

| 模块 | 核心功能 |
|------|----------|
| **简历解析** | 多格式简历(Word/PDF/图片/扫描件)→结构化JSON，批量处理≥50份，岗位匹配度，虚假信息检测 |
| **流式问答** | 流式卡片展示、意图识别、多类型卡片(表格/图表/表单)、RAG知识检索 |

### 1.3 POC环境要求

- 数据库：Elasticsearch 8.17
- 大模型：Qwen3-32B（阿里百炼平台）
- 验证数据集：20份模拟简历（多格式、多语言、多编码）
- 公网环境部署

---

## 2. 技术栈

| 层级 | 技术选型 |
|------|----------|
| **前端框架** | Vue3 + TypeScript + Vite |
| **UI组件库** | Element Plus + UI Pro Max（设计指导） |
| **前端状态** | Pinia |
| **图表库** | ECharts |
| **样式方案** | TailwindCSS |
| **后端框架** | FastAPI (Python 3.11+) |
| **包管理** | uv |
| **异步任务** | Celery + Redis |
| **数据库** | Elasticsearch 8.17 |
| **缓存** | Redis |
| **大模型** | Qwen3-32B（阿里百炼） |
| **OCR** | Qwen-VL-OCR（阿里百炼） |
| **文档解析** | pdfplumber / python-docx / chardet |
| **部署** | Docker Compose |

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue3 + Element Plus)                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   简历解析模块   │  │   智能问答模块   │  │   系统管理模块   │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼─────────────────────┼─────────────────────┼──────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ /api/resume │  │  /api/chat  │  │  /api/auth  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      业务服务层 (Python)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ ResumeParser │  │  ChatEngine  │  │  AuthService │           │
│  │   Service    │  │   Service    │  │              │           │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘           │
└─────────┼────────────────┼──────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      外部服务 & 存储                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ 阿里百炼平台  │  │    ES 8.17   │  │    Redis     │           │
│  │ Qwen3-32B    │  │   resumes    │  │   Session    │           │
│  │ Qwen-VL-OCR  │  │ knowledge_base│  │   Cache      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

**设计理念：**
- **单体应用 + 模块化**：POC阶段不过度拆分，但代码模块边界清晰
- **统一入口**：FastAPI 作为唯一后端入口
- **外部依赖最小化**：仅 ES + Redis + 阿里百炼API

---

## 4. 简历解析模块设计

### 4.1 处理流程

```
上传简历 → 文件类型检测 → 格式解析 → LLM结构化提取 → 后处理 → 存储ES
```

### 4.2 文件解析方案

| 文件类型 | 解析方案 |
|----------|----------|
| **图片/扫描件** | Qwen-VL-OCR（阿里百炼API） |
| **PDF** | pdfplumber |
| **Word (.docx)** | python-docx |
| **TXT** | 直接读取 + chardet编码检测 |

### 4.3 结构化输出Schema

```json
{
  "basic_info": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "age": "integer",
    "gender": "string"
  },
  "education": [{
    "school": "string",
    "degree": "string",
    "major": "string",
    "start_date": "date",
    "end_date": "date"
  }],
  "experience": [{
    "company": "string",
    "title": "string",
    "start_date": "date",
    "end_date": "date",
    "duties": "string"
  }],
  "skills": {
    "hard_skills": ["string"],
    "soft_skills": ["string"]
  },
  "job_intention": {
    "position": "string",
    "salary_min": "integer",
    "salary_max": "integer",
    "location": "string"
  },
  "warnings": [{
    "type": "string",
    "message": "string"
  }],
  "match_score": "float"
}
```

### 4.4 批量处理设计（≥50份）

- 使用 **Celery + Redis** 后台任务队列
- 前端 WebSocket 推送进度
- 失败自动重试（最多3次）
- 支持断点续传

---

## 5. 智能问答模块设计

### 5.1 处理流程

```
用户提问 → 意图识别 → ES知识检索 → RAG上下文构建 → Qwen3流式生成 → 前端渲染
```

### 5.2 流式响应技术

- **Server-Sent Events (SSE)**
- 首字响应目标：< 500ms
- 支持输出思考过程（可配置）

### 5.3 SSE响应格式

```
data: {"type": "thinking", "content": "正在分析问题..."}
data: {"type": "text", "content": "根据您的问题"}
data: {"type": "card", "card_type": "table", "data": {...}}
data: {"type": "done", "metrics": {"first_token_ms": 320}}
```

### 5.4 卡片类型（POC占位）

| 卡片类型 | 说明 |
|----------|------|
| TableCard | 信息表格展示 |
| ChartCard | 柱状/折线图 |
| FormCard | 表单提交 |

> 注：卡片系统已有现成方案，后续对接，POC仅做占位展示

### 5.5 异常处理

- 断网重连机制
- 超长文本截断提示
- 风险内容撤回（检测到敏感词立即停止并清除）

---

## 6. 项目目录结构

```
jianli_final/
├── frontend/                          # Vue3 前端
│   ├── src/
│   │   ├── api/                       # API 请求封装
│   │   │   ├── resume.ts
│   │   │   ├── chat.ts
│   │   │   └── auth.ts
│   │   ├── components/
│   │   │   ├── common/                # 通用组件
│   │   │   ├── resume/                # 简历模块组件
│   │   │   │   ├── ResumeUploader.vue
│   │   │   │   ├── ResumeList.vue
│   │   │   │   └── ResumeDetail.vue
│   │   │   ├── chat/                  # 问答模块组件
│   │   │   │   ├── ChatWindow.vue
│   │   │   │   ├── MessageBubble.vue
│   │   │   │   └── StreamRenderer.vue
│   │   │   └── cards/                 # 卡片组件（占位）
│   │   │       ├── TableCard.vue
│   │   │       ├── ChartCard.vue
│   │   │       └── FormCard.vue
│   │   ├── views/
│   │   │   ├── ResumeView.vue
│   │   │   ├── ChatView.vue
│   │   │   └── DashboardView.vue
│   │   ├── stores/                    # Pinia 状态管理
│   │   ├── router/
│   │   └── styles/                    # UI Pro Max 主题
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                           # Python FastAPI 后端
│   ├── pyproject.toml                 # uv 项目配置
│   ├── uv.lock
│   ├── .python-version
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── resume.py
│   │   │   │   ├── chat.py
│   │   │   │   └── auth.py
│   │   │   └── deps.py
│   │   ├── services/
│   │   │   ├── resume_parser.py
│   │   │   ├── file_processor.py
│   │   │   ├── llm_client.py
│   │   │   ├── chat_engine.py
│   │   │   └── es_client.py
│   │   ├── models/
│   │   ├── tasks/
│   │   │   └── batch_parse.py
│   │   └── utils/
│   │       ├── ocr.py
│   │       └── validators.py
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 7. 后端依赖 (pyproject.toml)

```toml
[project]
name = "resume-qa-backend"
version = "0.1.0"
description = "智能简历解析与流式问答POC"
requires-python = ">=3.11"
dependencies = [
    # Web 框架
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "python-multipart>=0.0.9",

    # 异步任务
    "celery>=5.4",
    "redis>=5.0",

    # 文档解析
    "pdfplumber>=0.11",
    "python-docx>=1.1",
    "chardet>=5.2",
    "Pillow>=10.0",

    # 阿里百炼 SDK
    "dashscope>=1.20",

    # Elasticsearch
    "elasticsearch>=8.17",

    # 数据验证
    "pydantic>=2.9",
    "pydantic-settings>=2.5",

    # 安全
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",

    # 工具
    "python-dotenv>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.6",
    "mypy>=1.11",
]
```

---

## 8. 前端依赖 (package.json)

```json
{
  "dependencies": {
    "vue": "^3.5.*",
    "vue-router": "^4.4.*",
    "pinia": "^2.2.*",
    "element-plus": "^2.8.*",
    "@element-plus/icons-vue": "^2.3.*",
    "axios": "^1.7.*",
    "@vueuse/core": "^11.*",
    "echarts": "^5.5.*",
    "vue-echarts": "^7.*"
  },
  "devDependencies": {
    "vite": "^5.4.*",
    "typescript": "^5.6.*",
    "@vitejs/plugin-vue": "^5.*",
    "tailwindcss": "^3.4.*",
    "autoprefixer": "^10.*",
    "postcss": "^8.*"
  }
}
```

---

## 9. ES 索引设计

### 9.1 简历索引 (resumes)

```json
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "file_name": { "type": "keyword" },
      "file_type": { "type": "keyword" },
      "raw_text": { "type": "text", "analyzer": "ik_max_word" },

      "basic_info": {
        "properties": {
          "name": { "type": "keyword" },
          "phone": { "type": "keyword" },
          "email": { "type": "keyword" },
          "age": { "type": "integer" },
          "gender": { "type": "keyword" }
        }
      },

      "education": {
        "type": "nested",
        "properties": {
          "school": { "type": "text", "fields": { "keyword": { "type": "keyword" }}},
          "degree": { "type": "keyword" },
          "major": { "type": "text" },
          "start_date": { "type": "date" },
          "end_date": { "type": "date" }
        }
      },

      "experience": {
        "type": "nested",
        "properties": {
          "company": { "type": "text", "fields": { "keyword": { "type": "keyword" }}},
          "title": { "type": "text" },
          "start_date": { "type": "date" },
          "end_date": { "type": "date" },
          "duties": { "type": "text", "analyzer": "ik_max_word" }
        }
      },

      "skills": {
        "properties": {
          "hard_skills": { "type": "keyword" },
          "soft_skills": { "type": "keyword" }
        }
      },

      "job_intention": {
        "properties": {
          "position": { "type": "text" },
          "salary_min": { "type": "integer" },
          "salary_max": { "type": "integer" },
          "location": { "type": "keyword" }
        }
      },

      "warnings": {
        "type": "nested",
        "properties": {
          "type": { "type": "keyword" },
          "message": { "type": "text" }
        }
      },

      "match_score": { "type": "float" },
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" }
    }
  }
}
```

### 9.2 知识库索引 (knowledge_base)

```json
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "title": { "type": "text", "analyzer": "ik_max_word" },
      "content": { "type": "text", "analyzer": "ik_max_word" },
      "category": { "type": "keyword" },
      "tags": { "type": "keyword" },
      "embedding": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      },
      "source": { "type": "keyword" },
      "created_at": { "type": "date" }
    }
  }
}
```

---

## 10. API 接口设计

### 10.1 简历解析 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/resume/upload` | 单份简历上传解析 |
| `POST` | `/api/resume/batch` | 批量上传（≥50份） |
| `GET` | `/api/resume/batch/{task_id}` | 查询批量任务进度 |
| `GET` | `/api/resume/list` | 简历列表（分页+筛选） |
| `GET` | `/api/resume/{id}` | 简历详情 |
| `GET` | `/api/resume/{id}/export` | 导出（JSON/XML/Excel） |
| `POST` | `/api/resume/match` | 岗位匹配度计算 |
| `DELETE` | `/api/resume/{id}` | 删除简历 |

### 10.2 智能问答 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat/message` | 发送消息（SSE流式响应） |
| `GET` | `/api/chat/history` | 获取对话历史 |
| `POST` | `/api/chat/session` | 创建新会话 |
| `DELETE` | `/api/chat/session/{id}` | 删除会话 |
| `POST` | `/api/knowledge/import` | 导入知识库数据 |
| `GET` | `/api/knowledge/list` | 知识库列表 |

### 10.3 认证 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/login` | 登录 |
| `POST` | `/api/auth/logout` | 登出 |
| `GET` | `/api/auth/me` | 当前用户信息 |

### 10.4 监控 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/metrics/performance` | 性能指标 |
| `GET` | `/api/metrics/errors` | 错误日志 |

---

## 11. 功能优先级

| 模块 | 功能点 | 优先级 |
|------|--------|--------|
| **简历解析** | 多格式支持（PDF/Word/TXT/图片） | P0 |
| | 结构化信息提取 | P0 |
| | 批量处理（≥50份） | P0 |
| | 虚假信息检测 | P1 |
| | 岗位匹配度 | P1 |
| | 多格式导出 | P1 |
| **智能问答** | 流式响应（SSE） | P0 |
| | 意图识别 | P0 |
| | RAG知识检索 | P0 |
| | 思考过程展示 | P1 |
| | 卡片渲染（占位） | P1 |
| | 异常处理/风险撤回 | P1 |
| **基础设施** | 用户认证 | P0 |
| | 接口鉴权/限流 | P1 |
| | 性能监控 | P2 |

---

## 12. Docker Compose 服务

```yaml
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:8.17.0
    # ES 配置...

  redis:
    image: redis:7-alpine
    # Redis 配置...

  backend:
    build: ./backend
    # FastAPI 服务...

  celery-worker:
    build: ./backend
    command: celery -A app.tasks worker
    # Celery 工作进程...

  frontend:
    build: ./frontend
    # Nginx + Vue3 静态资源...
```

---

## 13. 下一步行动

1. **项目初始化** - 创建前后端项目骨架
2. **Docker环境搭建** - ES + Redis 基础设施
3. **后端核心开发** - FastAPI框架、百炼SDK集成
4. **简历模块实现** - 文件解析、LLM提取、ES存储
5. **问答模块实现** - SSE流式、RAG检索
6. **前端页面开发** - Vue3 + Element Plus 界面
7. **联调测试** - 准备测试数据，端到端验证
