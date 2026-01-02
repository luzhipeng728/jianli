# 智能简历解析与流式问答助手

一个基于 RAG (检索增强生成) 技术的智能简历解析与问答系统，支持多种格式简历的解析、结构化信息提取、风险检测以及流式问答交互。

## 功能特性

- **多格式简历解析**：支持 PDF、Word (DOC/DOCX)、TXT、图片 (PNG/JPG) 等多种格式
- **RAG 驱动的智能问答**：基于检索增强生成技术，提供准确、上下文相关的流式问答
- **结构化信息提取**：自动提取姓名、联系方式、教育背景、工作经历、技能等关键信息
- **风险检测**：识别简历中的潜在风险点，如信息缺失、逻辑矛盾等
- **实时流式响应**：采用 SSE (Server-Sent Events) 技术实现流式对话体验
- **知识库管理**：支持简历知识的索引、检索和向量化存储
- **现代化界面**：基于 Vue3 + Element Plus 的响应式前端界面

## 技术栈

| 层级 | 技术栈 |
|------|--------|
| **前端** | Vue3 + Element Plus + TailwindCSS + TypeScript + Vite |
| **后端** | FastAPI + Python 3.11 + Pydantic |
| **搜索引擎** | Elasticsearch 8.17 |
| **缓存** | Redis 7 |
| **AI 模型** | 阿里百炼 Qwen3-32B (通义千问) |

## 快速开始

### 前置要求

- **Node.js** >= 18.0.0
- **Python** >= 3.11
- **Docker** 和 **Docker Compose** (用于运行 Elasticsearch 和 Redis)
- **阿里百炼 API Key** (从 [阿里云百炼平台](https://dashscope.aliyun.com/) 获取)

### 环境配置

1. **克隆项目**

```bash
git clone <repository-url>
cd jianli_final
```

2. **启动基础设施**

使用 Docker Compose 启动 Elasticsearch 和 Redis：

```bash
docker-compose up -d
```

3. **配置环境变量**

复制环境变量模板并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写必要的配置：

```bash
# Elasticsearch
ES_HOST=localhost
ES_PORT=9200

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 阿里百炼
DASHSCOPE_API_KEY=your_api_key_here

# JWT
JWT_SECRET=your_jwt_secret_here
```

4. **安装后端依赖**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

5. **安装前端依赖**

```bash
cd frontend
npm install
```

### 启动应用

#### 方式一：分别启动（开发模式）

**启动后端服务**（默认运行在 http://localhost:8000）：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端服务**（默认运行在 http://localhost:5173）：

```bash
cd frontend
npm run dev
```

#### 方式二：生产构建

**构建前端**：

```bash
cd frontend
npm run build
```

**启动后端**（会自动服务前端静态文件）：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 即可使用应用。

## 项目结构

```
jianli_final/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   └── routes/
│   │   │       ├── chat.py    # 聊天相关路由
│   │   │       ├── resume.py  # 简历相关路由
│   │   │       └── knowledge.py # 知识库路由
│   │   ├── models/            # Pydantic 数据模型
│   │   │   ├── chat.py        # 聊天模型
│   │   │   └── resume.py      # 简历模型
│   │   ├── services/          # 核心业务逻辑
│   │   │   ├── chat_engine.py     # 对话引擎
│   │   │   ├── resume_parser.py   # 简历解析器
│   │   │   ├── knowledge_base.py  # 知识库管理
│   │   │   └── llm_client.py      # LLM 客户端
│   │   ├── tasks/             # 异步任务
│   │   ├── utils/             # 工具函数
│   │   └── main.py            # FastAPI 应用入口
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── api/               # API 客户端
│   │   ├── components/        # Vue 组件
│   │   │   ├── chat/          # 聊天组件
│   │   │   └── resume/        # 简历组件
│   │   ├── layouts/           # 布局组件
│   │   ├── router/            # 路由配置
│   │   ├── styles/            # 样式文件
│   │   ├── views/             # 页面视图
│   │   │   ├── DashboardView.vue  # 仪表板
│   │   │   ├── ResumeView.vue     # 简历管理
│   │   │   └── ChatView.vue       # 问答界面
│   │   ├── App.vue            # 根组件
│   │   └── main.ts            # 应用入口
│   ├── package.json           # NPM 依赖
│   └── vite.config.ts         # Vite 配置
│
├── tests/                      # 测试文件
│   └── samples/               # 测试样本
├── docs/                       # 项目文档
├── docker-compose.yml         # Docker 编排配置
├── .env.example               # 环境变量模板
├── .gitignore                 # Git 忽略文件
└── README.md                  # 项目说明文档
```

## API 接口

### 简历相关接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/resume/upload` | 上传并解析单份简历 |
| `GET` | `/api/resume/list` | 获取简历列表（分页） |
| `GET` | `/api/resume/{resume_id}` | 获取简历详情 |
| `DELETE` | `/api/resume/{resume_id}` | 删除指定简历 |

**上传简历示例**：

```bash
curl -X POST http://localhost:8000/api/resume/upload \
  -F "file=@resume.pdf"
```

**响应示例**：

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "resume.pdf",
    "name": "张三",
    "contact": {
      "phone": "138****8888",
      "email": "zhangsan@example.com"
    },
    "education": [...],
    "experience": [...],
    "skills": [...],
    "risks": []
  }
}
```

### 聊天相关接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat/session` | 创建新的对话会话 |
| `DELETE` | `/api/chat/session/{session_id}` | 删除指定会话 |
| `GET` | `/api/chat/history/{session_id}` | 获取对话历史 |
| `POST` | `/api/chat/message` | 发送消息（SSE 流式响应） |

**创建会话示例**：

```bash
curl -X POST http://localhost:8000/api/chat/session
```

**发送消息示例**：

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "message": "这位候选人的工作经验如何？",
    "show_thinking": true
  }'
```

**SSE 流式响应**：

```
data: {"type":"thinking","content":"正在分析候选人工作经验..."}

data: {"type":"knowledge","content":"[检索到的相关知识]"}

data: {"type":"answer","content":"该候选人有5年Python开发经验..."}

data: {"type":"done"}
```

### 知识库接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/knowledge/index/{resume_id}` | 为简历创建知识库索引 |
| `POST` | `/api/knowledge/search` | 搜索相关知识片段 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 服务健康检查 |

## 开发说明

### 后端开发

- **代码规范**：遵循 PEP 8 规范
- **类型提示**：所有函数和方法都包含完整的类型注解
- **文档字符串**：使用中文文档字符串说明函数用途
- **错误处理**：统一使用 HTTPException 处理错误

### 前端开发

- **组件规范**：使用 Composition API 和 `<script setup>` 语法
- **状态管理**：使用 Pinia 管理全局状态
- **样式方案**：Tailwind CSS + Element Plus
- **类型安全**：TypeScript 严格模式

### 测试

运行测试（待实现）：

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

## 部署

### Docker 部署（推荐）

待补充完整的 Dockerfile 和生产环境 Docker Compose 配置。

### 传统部署

1. 配置 Nginx 反向代理
2. 使用 systemd 管理后端服务
3. 前端构建后部署到 Nginx 静态目录

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至项目维护者

---

**注意**：本项目仅供学习和研究使用，生产环境部署前请务必进行充分的安全加固和性能优化。
