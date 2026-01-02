# 智能简历解析与流式问答助手 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建集成简历解析和流式问答的POC系统

**Architecture:** 前后端分离架构，Vue3前端 + FastAPI后端，ES存储，阿里百炼大模型

**Tech Stack:** Vue3/Element Plus/TailwindCSS | FastAPI/uv/Celery | ES 8.17/Redis | Qwen3-32B/Qwen-VL-OCR

---

## Phase 1: 项目初始化与基础设施

### Task 1.1: 创建后端项目骨架

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

**Step 1: 创建后端目录结构**

```bash
mkdir -p backend/app/{api/routes,services,models,tasks,utils}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/routes/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/app/tasks/__init__.py
touch backend/app/utils/__init__.py
```

**Step 2: 创建 pyproject.toml**

```toml
[project]
name = "resume-qa-backend"
version = "0.1.0"
description = "智能简历解析与流式问答POC"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "python-multipart>=0.0.9",
    "pydantic>=2.9",
    "pydantic-settings>=2.5",
    "python-dotenv>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.6",
]
```

**Step 3: 创建 .python-version**

```
3.11
```

**Step 4: 创建 app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="简历解析与问答助手",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**Step 5: 初始化 uv 并安装依赖**

```bash
cd backend && uv sync
```

**Step 6: 验证后端启动**

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
# 访问 http://localhost:8000/health 应返回 {"status": "ok"}
```

**Step 7: 提交**

```bash
git add backend/
git commit -m "feat(backend): 初始化FastAPI项目骨架"
```

---

### Task 1.2: 创建前端项目骨架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`

**Step 1: 使用 Vite 创建 Vue3 项目**

```bash
npm create vite@latest frontend -- --template vue-ts
cd frontend && npm install
```

**Step 2: 安装核心依赖**

```bash
cd frontend
npm install element-plus @element-plus/icons-vue vue-router pinia axios @vueuse/core
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Step 3: 验证前端启动**

```bash
cd frontend && npm run dev
# 访问 http://localhost:5173 应看到 Vue 欢迎页
```

**Step 4: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): 初始化Vue3+Vite项目"
```

---

### Task 1.3: 创建 Docker Compose 基础设施

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0
    container_name: resume-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  redis:
    image: redis:7-alpine
    container_name: resume-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  es_data:
  redis_data:
```

**Step 2: 创建 .env.example**

```env
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

**Step 3: 启动基础设施**

```bash
docker-compose up -d elasticsearch redis
```

**Step 4: 验证 ES 和 Redis**

```bash
curl http://localhost:9200/_cluster/health
redis-cli ping
```

**Step 5: 提交**

```bash
git add docker-compose.yml .env.example
git commit -m "infra: 添加Docker Compose配置(ES+Redis)"
```

---

## Phase 2: 后端核心服务

### Task 2.1: 配置管理模块

**Files:**
- Create: `backend/app/config.py`
- Modify: `backend/pyproject.toml` (添加依赖)

**Step 1: 更新 pyproject.toml 添加新依赖**

```toml
# 在 dependencies 中添加
    "elasticsearch>=8.17",
    "redis>=5.0",
    "dashscope>=1.20",
```

**Step 2: 创建 config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    app_name: str = "简历解析与问答助手"
    debug: bool = False

    # Elasticsearch
    es_host: str = "localhost"
    es_port: int = 9200

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # 阿里百炼
    dashscope_api_key: str = ""

    # JWT
    jwt_secret: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24小时

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 3: 同步依赖**

```bash
cd backend && uv sync
```

**Step 4: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加配置管理模块"
```

---

### Task 2.2: Elasticsearch 客户端封装

**Files:**
- Create: `backend/app/services/es_client.py`
- Create: `backend/tests/test_es_client.py`

**Step 1: 创建测试文件**

```python
# backend/tests/test_es_client.py
import pytest
from app.services.es_client import ESClient

@pytest.fixture
def es_client():
    return ESClient()

def test_es_client_ping(es_client):
    """测试ES连接"""
    assert es_client.ping() is True

def test_create_index(es_client):
    """测试创建索引"""
    index_name = "test_index"
    result = es_client.create_index(index_name, {"mappings": {"properties": {}}})
    assert result is True
    # 清理
    es_client.delete_index(index_name)
```

**Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_es_client.py -v
# Expected: FAIL - 模块不存在
```

**Step 3: 创建 es_client.py**

```python
from elasticsearch import Elasticsearch
from app.config import get_settings

class ESClient:
    def __init__(self):
        settings = get_settings()
        self.client = Elasticsearch(
            hosts=[f"http://{settings.es_host}:{settings.es_port}"]
        )

    def ping(self) -> bool:
        return self.client.ping()

    def create_index(self, index_name: str, body: dict) -> bool:
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name, body=body)
        return True

    def delete_index(self, index_name: str) -> bool:
        if self.client.indices.exists(index=index_name):
            self.client.indices.delete(index=index_name)
        return True

    def index_document(self, index_name: str, doc_id: str, document: dict):
        return self.client.index(index=index_name, id=doc_id, document=document)

    def get_document(self, index_name: str, doc_id: str):
        return self.client.get(index=index_name, id=doc_id)

    def search(self, index_name: str, query: dict):
        return self.client.search(index=index_name, body=query)

    def delete_document(self, index_name: str, doc_id: str):
        return self.client.delete(index=index_name, id=doc_id)
```

**Step 4: 运行测试确认通过**

```bash
cd backend && uv run pytest tests/test_es_client.py -v
# Expected: PASS
```

**Step 5: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加ES客户端封装"
```

---

### Task 2.3: 阿里百炼 LLM 客户端

**Files:**
- Create: `backend/app/services/llm_client.py`
- Create: `backend/tests/test_llm_client.py`

**Step 1: 创建测试文件**

```python
# backend/tests/test_llm_client.py
import pytest
from app.services.llm_client import LLMClient

@pytest.fixture
def llm_client():
    return LLMClient()

def test_llm_client_init(llm_client):
    """测试LLM客户端初始化"""
    assert llm_client is not None

@pytest.mark.asyncio
async def test_chat_completion(llm_client):
    """测试对话完成（需要真实API Key）"""
    # 跳过如果没有配置API Key
    if not llm_client.api_key:
        pytest.skip("DASHSCOPE_API_KEY not configured")

    response = await llm_client.chat("你好")
    assert response is not None
    assert len(response) > 0
```

**Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_llm_client.py -v
# Expected: FAIL - 模块不存在
```

**Step 3: 创建 llm_client.py**

```python
import dashscope
from dashscope import Generation
from typing import AsyncGenerator
from app.config import get_settings

class LLMClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.dashscope_api_key
        dashscope.api_key = self.api_key
        self.model = "qwen-max"  # 或 qwen3-32b

    async def chat(self, prompt: str, system_prompt: str = "") -> str:
        """同步对话"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = Generation.call(
            model=self.model,
            messages=messages,
            result_format="message",
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        return ""

    async def chat_stream(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        responses = Generation.call(
            model=self.model,
            messages=messages,
            result_format="message",
            stream=True,
            incremental_output=True,
        )

        for response in responses:
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if content:
                    yield content

    async def ocr(self, image_url: str) -> str:
        """使用Qwen-VL-OCR进行图片文字识别"""
        messages = [{
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": "请识别图片中的所有文字内容，保持原有格式。"}
            ]
        }]

        response = Generation.call(
            model="qwen-vl-ocr",
            messages=messages,
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        return ""
```

**Step 4: 运行测试**

```bash
cd backend && uv run pytest tests/test_llm_client.py -v
# Expected: PASS (跳过需要API Key的测试)
```

**Step 5: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加阿里百炼LLM客户端"
```

---

## Phase 3: 简历解析模块

### Task 3.1: 文件处理器

**Files:**
- Create: `backend/app/services/file_processor.py`
- Modify: `backend/pyproject.toml` (添加文档解析依赖)

**Step 1: 更新 pyproject.toml**

```toml
# 在 dependencies 中添加
    "pdfplumber>=0.11",
    "python-docx>=1.1",
    "chardet>=5.2",
    "Pillow>=10.0",
```

**Step 2: 同步依赖**

```bash
cd backend && uv sync
```

**Step 3: 创建 file_processor.py**

```python
import io
import chardet
import pdfplumber
from docx import Document
from PIL import Image
from pathlib import Path
from enum import Enum

class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"
    UNKNOWN = "unknown"

class FileProcessor:
    SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def detect_file_type(self, filename: str) -> FileType:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return FileType.PDF
        elif suffix in {".docx", ".doc"}:
            return FileType.DOCX
        elif suffix == ".txt":
            return FileType.TXT
        elif suffix in self.SUPPORTED_IMAGES:
            return FileType.IMAGE
        return FileType.UNKNOWN

    def extract_text_from_pdf(self, file_content: bytes) -> str:
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def extract_text_from_docx(self, file_content: bytes) -> str:
        doc = Document(io.BytesIO(file_content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def extract_text_from_txt(self, file_content: bytes) -> str:
        detected = chardet.detect(file_content)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        return file_content.decode(encoding)

    def process_file(self, filename: str, content: bytes) -> tuple[FileType, str]:
        file_type = self.detect_file_type(filename)

        if file_type == FileType.PDF:
            text = self.extract_text_from_pdf(content)
        elif file_type == FileType.DOCX:
            text = self.extract_text_from_docx(content)
        elif file_type == FileType.TXT:
            text = self.extract_text_from_txt(content)
        elif file_type == FileType.IMAGE:
            text = ""  # 需要OCR处理，返回空，由上层调用LLM OCR
        else:
            text = ""

        return file_type, text
```

**Step 4: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加文件处理器(PDF/DOCX/TXT)"
```

---

### Task 3.2: 简历数据模型

**Files:**
- Create: `backend/app/models/resume.py`

**Step 1: 创建 resume.py**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class Education(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class Experience(BaseModel):
    company: str = ""
    title: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duties: str = ""

class Skills(BaseModel):
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

class JobIntention(BaseModel):
    position: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: str = ""

class Warning(BaseModel):
    type: str  # fake_education, time_conflict, etc.
    message: str

class BasicInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    age: Optional[int] = None
    gender: str = ""

class ResumeData(BaseModel):
    id: str = ""
    file_name: str = ""
    file_type: str = ""
    raw_text: str = ""
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    job_intention: JobIntention = Field(default_factory=JobIntention)
    warnings: list[Warning] = Field(default_factory=list)
    match_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ResumeUploadResponse(BaseModel):
    id: str
    status: str
    data: Optional[ResumeData] = None
    error: Optional[str] = None
```

**Step 2: 提交**

```bash
git add backend/app/models/
git commit -m "feat(backend): 添加简历数据模型"
```

---

### Task 3.3: 简历解析服务

**Files:**
- Create: `backend/app/services/resume_parser.py`

**Step 1: 创建 resume_parser.py**

```python
import uuid
import json
from app.services.file_processor import FileProcessor, FileType
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.models.resume import ResumeData, BasicInfo, Education, Experience, Skills, JobIntention, Warning

RESUME_INDEX = "resumes"

EXTRACT_PROMPT = """请从以下简历文本中提取结构化信息，以JSON格式返回。

要求提取的字段：
1. basic_info: name(姓名), phone(电话), email(邮箱), age(年龄), gender(性别)
2. education: 数组，每项包含 school(学校), degree(学历), major(专业), start_date, end_date
3. experience: 数组，每项包含 company(公司), title(职位), start_date, end_date, duties(职责)
4. skills: hard_skills(硬技能数组), soft_skills(软技能数组)
5. job_intention: position(期望职位), salary_min, salary_max, location(期望地点)
6. warnings: 检测到的问题，如时间矛盾、可疑信息等

简历文本：
{text}

请仅返回JSON，不要添加任何解释。"""

class ResumeParser:
    def __init__(self):
        self.file_processor = FileProcessor()
        self.llm_client = LLMClient()
        self.es_client = ESClient()

    async def parse(self, filename: str, content: bytes) -> ResumeData:
        # 1. 提取文本
        file_type, text = self.file_processor.process_file(filename, content)

        # 2. 如果是图片，使用OCR
        if file_type == FileType.IMAGE:
            # 需要先上传图片获取URL，这里简化处理
            # 实际实现需要将图片上传到OSS或本地服务
            text = "图片OCR暂未实现"

        # 3. 使用LLM提取结构化信息
        prompt = EXTRACT_PROMPT.format(text=text[:8000])  # 限制长度
        result = await self.llm_client.chat(prompt)

        # 4. 解析JSON结果
        resume_data = self._parse_llm_result(result, filename, file_type.value, text)

        # 5. 存储到ES
        self._save_to_es(resume_data)

        return resume_data

    def _parse_llm_result(
        self, result: str, filename: str, file_type: str, raw_text: str
    ) -> ResumeData:
        try:
            # 提取JSON部分
            result = result.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            data = json.loads(result)
        except json.JSONDecodeError:
            data = {}

        resume_id = str(uuid.uuid4())

        return ResumeData(
            id=resume_id,
            file_name=filename,
            file_type=file_type,
            raw_text=raw_text,
            basic_info=BasicInfo(**data.get("basic_info", {})),
            education=[Education(**e) for e in data.get("education", [])],
            experience=[Experience(**e) for e in data.get("experience", [])],
            skills=Skills(**data.get("skills", {})),
            job_intention=JobIntention(**data.get("job_intention", {})),
            warnings=[Warning(**w) for w in data.get("warnings", [])],
        )

    def _save_to_es(self, resume: ResumeData):
        self.es_client.index_document(
            RESUME_INDEX,
            resume.id,
            resume.model_dump(mode="json")
        )

    def get_resume(self, resume_id: str) -> ResumeData | None:
        try:
            result = self.es_client.get_document(RESUME_INDEX, resume_id)
            return ResumeData(**result["_source"])
        except Exception:
            return None

    def list_resumes(self, page: int = 1, size: int = 20) -> list[ResumeData]:
        query = {
            "query": {"match_all": {}},
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"created_at": "desc"}]
        }
        result = self.es_client.search(RESUME_INDEX, query)
        return [ResumeData(**hit["_source"]) for hit in result["hits"]["hits"]]

    def delete_resume(self, resume_id: str) -> bool:
        try:
            self.es_client.delete_document(RESUME_INDEX, resume_id)
            return True
        except Exception:
            return False
```

**Step 2: 提交**

```bash
git add backend/app/services/
git commit -m "feat(backend): 添加简历解析服务"
```

---

### Task 3.4: 简历解析 API 路由

**Files:**
- Create: `backend/app/api/routes/resume.py`
- Modify: `backend/app/main.py` (注册路由)

**Step 1: 创建 resume.py 路由**

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.resume_parser import ResumeParser
from app.models.resume import ResumeData, ResumeUploadResponse

router = APIRouter(prefix="/api/resume", tags=["简历解析"])

parser = ResumeParser()

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """上传并解析单份简历"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB限制
        raise HTTPException(400, "文件大小超过10MB限制")

    try:
        resume = await parser.parse(file.filename, content)
        return ResumeUploadResponse(id=resume.id, status="success", data=resume)
    except Exception as e:
        return ResumeUploadResponse(id="", status="error", error=str(e))

@router.get("/list")
async def list_resumes(page: int = 1, size: int = 20):
    """获取简历列表"""
    resumes = parser.list_resumes(page, size)
    return {"data": resumes, "page": page, "size": size}

@router.get("/{resume_id}", response_model=ResumeData)
async def get_resume(resume_id: str):
    """获取简历详情"""
    resume = parser.get_resume(resume_id)
    if not resume:
        raise HTTPException(404, "简历不存在")
    return resume

@router.delete("/{resume_id}")
async def delete_resume(resume_id: str):
    """删除简历"""
    success = parser.delete_resume(resume_id)
    if not success:
        raise HTTPException(404, "简历不存在")
    return {"status": "deleted"}
```

**Step 2: 更新 main.py 注册路由**

```python
# 在 main.py 中添加
from app.api.routes import resume

app.include_router(resume.router)
```

**Step 3: 验证 API**

```bash
cd backend && uv run uvicorn app.main:app --reload
# 访问 http://localhost:8000/docs 查看Swagger文档
```

**Step 4: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加简历解析API路由"
```

---

## Phase 4: 智能问答模块

### Task 4.1: 问答数据模型

**Files:**
- Create: `backend/app/models/chat.py`

**Step 1: 创建 chat.py**

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    show_thinking: bool = False

class StreamChunk(BaseModel):
    type: Literal["thinking", "text", "card", "done", "error"]
    content: str = ""
    card_type: Optional[str] = None
    data: Optional[dict] = None
    metrics: Optional[dict] = None

class KnowledgeItem(BaseModel):
    id: str
    title: str
    content: str
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
```

**Step 2: 提交**

```bash
git add backend/app/models/
git commit -m "feat(backend): 添加问答数据模型"
```

---

### Task 4.2: 问答引擎服务

**Files:**
- Create: `backend/app/services/chat_engine.py`

**Step 1: 创建 chat_engine.py**

```python
import uuid
import time
import json
from typing import AsyncGenerator
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.models.chat import ChatMessage, ChatSession, StreamChunk

KNOWLEDGE_INDEX = "knowledge_base"

SYSTEM_PROMPT = """你是一个智能问答助手，能够回答用户的问题。
请基于提供的上下文信息回答问题，如果上下文中没有相关信息，请基于你的知识回答。
回答要简洁、准确、有帮助。

当需要展示结构化数据时，可以使用以下卡片格式：
- 表格数据: <card:table>{"headers":["列1","列2"],"rows":[["值1","值2"]]}</card:table>
- 图表数据: <card:chart>{"type":"bar","data":[...]}</card:chart>
"""

class ChatEngine:
    def __init__(self):
        self.llm_client = LLMClient()
        self.es_client = ESClient()
        self.sessions: dict[str, ChatSession] = {}

    def create_session(self) -> ChatSession:
        session = ChatSession(id=str(uuid.uuid4()))
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def _search_knowledge(self, query: str, top_k: int = 3) -> list[dict]:
        """从知识库检索相关内容"""
        try:
            search_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"],
                        "type": "best_fields"
                    }
                },
                "size": top_k
            }
            result = self.es_client.search(KNOWLEDGE_INDEX, search_query)
            return [hit["_source"] for hit in result["hits"]["hits"]]
        except Exception:
            return []

    def _build_context(self, query: str, history: list[ChatMessage]) -> str:
        """构建RAG上下文"""
        # 检索知识库
        knowledge = self._search_knowledge(query)

        context_parts = []

        # 添加知识库内容
        if knowledge:
            context_parts.append("相关知识：")
            for i, item in enumerate(knowledge, 1):
                context_parts.append(f"{i}. {item.get('title', '')}: {item.get('content', '')[:500]}")

        # 添加历史对话（最近5轮）
        recent_history = history[-10:]  # 最近5轮对话
        if recent_history:
            context_parts.append("\n历史对话：")
            for msg in recent_history:
                role = "用户" if msg.role == "user" else "助手"
                context_parts.append(f"{role}: {msg.content[:200]}")

        return "\n".join(context_parts)

    async def chat_stream(
        self,
        session_id: str | None,
        message: str,
        show_thinking: bool = False
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式问答"""
        start_time = time.time()
        first_token_time = None

        # 获取或创建会话
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = self.create_session()

        # 添加用户消息
        session.messages.append(ChatMessage(role="user", content=message))

        # 构建上下文
        context = self._build_context(message, session.messages[:-1])

        # 构建完整prompt
        full_prompt = f"{context}\n\n用户问题：{message}"

        # 思考过程
        if show_thinking:
            yield StreamChunk(type="thinking", content="正在分析问题...")

        # 流式生成
        full_response = ""
        async for chunk in self.llm_client.chat_stream(full_prompt, SYSTEM_PROMPT):
            if first_token_time is None:
                first_token_time = time.time()

            full_response += chunk

            # 检测卡片标记
            if "<card:" in chunk:
                # 简化处理，实际需要更复杂的解析
                yield StreamChunk(type="text", content=chunk)
            else:
                yield StreamChunk(type="text", content=chunk)

        # 添加助手回复到历史
        session.messages.append(ChatMessage(role="assistant", content=full_response))

        # 完成
        end_time = time.time()
        metrics = {
            "first_token_ms": int((first_token_time - start_time) * 1000) if first_token_time else 0,
            "total_ms": int((end_time - start_time) * 1000),
            "session_id": session.id
        }
        yield StreamChunk(type="done", metrics=metrics)
```

**Step 2: 提交**

```bash
git add backend/app/services/
git commit -m "feat(backend): 添加问答引擎服务"
```

---

### Task 4.3: SSE 流式响应 API

**Files:**
- Create: `backend/app/api/routes/chat.py`
- Modify: `backend/app/main.py` (注册路由)

**Step 1: 创建 chat.py 路由**

```python
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.chat_engine import ChatEngine
from app.models.chat import ChatRequest, ChatSession, KnowledgeItem

router = APIRouter(prefix="/api/chat", tags=["智能问答"])

engine = ChatEngine()

@router.post("/session")
async def create_session() -> ChatSession:
    """创建新会话"""
    return engine.create_session()

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if not engine.delete_session(session_id):
        raise HTTPException(404, "会话不存在")
    return {"status": "deleted"}

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """获取对话历史"""
    session = engine.get_session(session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    return {"messages": session.messages}

@router.post("/message")
async def chat_message(request: ChatRequest):
    """发送消息（SSE流式响应）"""

    async def generate():
        async for chunk in engine.chat_stream(
            request.session_id,
            request.message,
            request.show_thinking
        ):
            data = chunk.model_dump_json()
            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

**Step 2: 更新 main.py 注册路由**

```python
# 在 main.py 中添加
from app.api.routes import chat

app.include_router(chat.router)
```

**Step 3: 验证 SSE**

```bash
# 终端1: 启动服务
cd backend && uv run uvicorn app.main:app --reload

# 终端2: 测试SSE
curl -N -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

**Step 4: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加SSE流式问答API"
```

---

### Task 4.4: 知识库管理 API

**Files:**
- Create: `backend/app/api/routes/knowledge.py`
- Modify: `backend/app/main.py` (注册路由)

**Step 1: 创建 knowledge.py 路由**

```python
import uuid
from fastapi import APIRouter, HTTPException
from app.services.es_client import ESClient
from app.models.chat import KnowledgeItem

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

KNOWLEDGE_INDEX = "knowledge_base"
es_client = ESClient()

@router.post("/import")
async def import_knowledge(items: list[KnowledgeItem]):
    """批量导入知识"""
    for item in items:
        if not item.id:
            item.id = str(uuid.uuid4())
        es_client.index_document(
            KNOWLEDGE_INDEX,
            item.id,
            item.model_dump(mode="json")
        )
    return {"status": "success", "count": len(items)}

@router.get("/list")
async def list_knowledge(page: int = 1, size: int = 20):
    """获取知识列表"""
    query = {
        "query": {"match_all": {}},
        "from": (page - 1) * size,
        "size": size,
        "sort": [{"created_at": "desc"}]
    }
    try:
        result = es_client.search(KNOWLEDGE_INDEX, query)
        items = [hit["_source"] for hit in result["hits"]["hits"]]
        total = result["hits"]["total"]["value"]
        return {"data": items, "total": total, "page": page, "size": size}
    except Exception:
        return {"data": [], "total": 0, "page": page, "size": size}

@router.delete("/{item_id}")
async def delete_knowledge(item_id: str):
    """删除知识条目"""
    try:
        es_client.delete_document(KNOWLEDGE_INDEX, item_id)
        return {"status": "deleted"}
    except Exception:
        raise HTTPException(404, "条目不存在")
```

**Step 2: 更新 main.py 注册路由**

```python
# 在 main.py 中添加
from app.api.routes import knowledge

app.include_router(knowledge.router)
```

**Step 3: 提交**

```bash
git add backend/
git commit -m "feat(backend): 添加知识库管理API"
```

---

## Phase 5: 前端开发

### Task 5.1: 前端基础配置

**Files:**
- Modify: `frontend/src/main.ts`
- Modify: `frontend/tailwind.config.js`
- Create: `frontend/src/styles/index.css`

**Step 1: 配置 main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles/index.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
```

**Step 2: 配置 tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#409eff',
        success: '#67c23a',
        warning: '#e6a23c',
        danger: '#f56c6c',
      }
    },
  },
  plugins: [],
}
```

**Step 3: 创建 styles/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --el-color-primary: #409eff;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 自定义滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

::-webkit-scrollbar-track {
  background: #f5f7fa;
}
```

**Step 4: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): 配置Element Plus和TailwindCSS"
```

---

### Task 5.2: 路由和布局

**Files:**
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/MainLayout.vue`
- Modify: `frontend/src/App.vue`

**Step 1: 创建 router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'resume',
          name: 'Resume',
          component: () => import('@/views/ResumeView.vue'),
        },
        {
          path: 'chat',
          name: 'Chat',
          component: () => import('@/views/ChatView.vue'),
        },
      ],
    },
  ],
})

export default router
```

**Step 2: 创建 layouts/MainLayout.vue**

```vue
<template>
  <el-container class="h-screen">
    <el-aside width="200px" class="bg-gray-900">
      <div class="p-4 text-white text-xl font-bold">
        智能简历助手
      </div>
      <el-menu
        :default-active="route.path"
        class="border-none"
        background-color="#111827"
        text-color="#9ca3af"
        active-text-color="#fff"
        router
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/resume">
          <el-icon><Document /></el-icon>
          <span>简历解析</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-main class="bg-gray-50 p-6">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
```

**Step 3: 更新 App.vue**

```vue
<template>
  <router-view />
</template>
```

**Step 4: 创建占位视图**

```bash
mkdir -p frontend/src/views frontend/src/layouts
```

创建 `frontend/src/views/DashboardView.vue`:

```vue
<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">仪表盘</h1>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <div class="text-gray-500">简历总数</div>
          <div class="text-3xl font-bold mt-2">0</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="text-gray-500">今日解析</div>
          <div class="text-3xl font-bold mt-2">0</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="text-gray-500">问答次数</div>
          <div class="text-3xl font-bold mt-2">0</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
```

**Step 5: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): 添加路由和主布局"
```

---

### Task 5.3: API 请求封装

**Files:**
- Create: `frontend/src/api/request.ts`
- Create: `frontend/src/api/resume.ts`
- Create: `frontend/src/api/chat.ts`

**Step 1: 创建 request.ts**

```typescript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)

export default request
```

**Step 2: 创建 resume.ts**

```typescript
import request from './request'

export interface ResumeData {
  id: string
  file_name: string
  file_type: string
  basic_info: {
    name: string
    phone: string
    email: string
    age?: number
    gender: string
  }
  education: Array<{
    school: string
    degree: string
    major: string
  }>
  experience: Array<{
    company: string
    title: string
    duties: string
  }>
  skills: {
    hard_skills: string[]
    soft_skills: string[]
  }
  warnings: Array<{
    type: string
    message: string
  }>
  created_at: string
}

export const uploadResume = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/resume/upload', formData)
}

export const getResumeList = (page = 1, size = 20) => {
  return request.get('/api/resume/list', { params: { page, size } })
}

export const getResume = (id: string) => {
  return request.get(`/api/resume/${id}`)
}

export const deleteResume = (id: string) => {
  return request.delete(`/api/resume/${id}`)
}
```

**Step 3: 创建 chat.ts**

```typescript
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface StreamChunk {
  type: 'thinking' | 'text' | 'card' | 'done' | 'error'
  content?: string
  card_type?: string
  data?: any
  metrics?: {
    first_token_ms: number
    total_ms: number
    session_id: string
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function* chatStream(
  message: string,
  sessionId?: string,
  showThinking = false
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE}/api/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      show_thinking: showThinking,
    }),
  })

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) return

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const chunk: StreamChunk = JSON.parse(line.slice(6))
          yield chunk
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}
```

**Step 4: 提交**

```bash
git add frontend/src/api/
git commit -m "feat(frontend): 添加API请求封装"
```

---

### Task 5.4: 简历解析页面

**Files:**
- Create: `frontend/src/views/ResumeView.vue`
- Create: `frontend/src/components/resume/ResumeUploader.vue`
- Create: `frontend/src/components/resume/ResumeList.vue`

**Step 1: 创建 ResumeUploader.vue**

```vue
<template>
  <el-upload
    class="w-full"
    drag
    :auto-upload="false"
    :on-change="handleChange"
    :show-file-list="false"
    accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png"
  >
    <el-icon class="text-4xl text-gray-400"><UploadFilled /></el-icon>
    <div class="el-upload__text">
      拖拽文件到此处，或 <em>点击上传</em>
    </div>
    <template #tip>
      <div class="el-upload__tip">
        支持 PDF、Word、TXT、图片格式，单文件不超过10MB
      </div>
    </template>
  </el-upload>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { uploadResume } from '@/api/resume'

const emit = defineEmits(['success'])

const handleChange = async (uploadFile: any) => {
  if (!uploadFile.raw) return

  const loading = ElMessage.info({ message: '正在解析...', duration: 0 })

  try {
    const result = await uploadResume(uploadFile.raw)
    loading.close()

    if (result.status === 'success') {
      ElMessage.success('解析成功')
      emit('success', result.data)
    } else {
      ElMessage.error(result.error || '解析失败')
    }
  } catch (e) {
    loading.close()
    ElMessage.error('上传失败')
  }
}
</script>
```

**Step 2: 创建 ResumeList.vue**

```vue
<template>
  <el-table :data="resumes" v-loading="loading">
    <el-table-column prop="basic_info.name" label="姓名" width="100" />
    <el-table-column prop="basic_info.phone" label="电话" width="140" />
    <el-table-column prop="file_name" label="文件名" />
    <el-table-column prop="file_type" label="类型" width="80" />
    <el-table-column label="技能" min-width="200">
      <template #default="{ row }">
        <el-tag
          v-for="skill in row.skills?.hard_skills?.slice(0, 3)"
          :key="skill"
          size="small"
          class="mr-1"
        >
          {{ skill }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="预警" width="100">
      <template #default="{ row }">
        <el-badge v-if="row.warnings?.length" :value="row.warnings.length" type="danger" />
        <span v-else class="text-gray-400">-</span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120">
      <template #default="{ row }">
        <el-button size="small" @click="$emit('view', row)">查看</el-button>
        <el-button size="small" type="danger" @click="$emit('delete', row.id)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { ResumeData } from '@/api/resume'

defineProps<{
  resumes: ResumeData[]
  loading: boolean
}>()

defineEmits(['view', 'delete'])
</script>
```

**Step 3: 创建 ResumeView.vue**

```vue
<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">简历解析</h1>

    <el-card class="mb-4">
      <ResumeUploader @success="handleUploadSuccess" />
    </el-card>

    <el-card>
      <template #header>
        <div class="flex justify-between items-center">
          <span>简历列表</span>
          <el-button @click="loadResumes">刷新</el-button>
        </div>
      </template>
      <ResumeList
        :resumes="resumes"
        :loading="loading"
        @view="handleView"
        @delete="handleDelete"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="dialogVisible" title="简历详情" width="600px">
      <template v-if="currentResume">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ currentResume.basic_info.name }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ currentResume.basic_info.phone }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentResume.basic_info.email }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ currentResume.basic_info.gender }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="mt-4 mb-2 font-bold">教育经历</h4>
        <div v-for="edu in currentResume.education" :key="edu.school" class="mb-2">
          {{ edu.school }} - {{ edu.degree }} {{ edu.major }}
        </div>

        <h4 class="mt-4 mb-2 font-bold">工作经历</h4>
        <div v-for="exp in currentResume.experience" :key="exp.company" class="mb-2">
          <strong>{{ exp.company }}</strong> - {{ exp.title }}
          <p class="text-gray-600 text-sm">{{ exp.duties }}</p>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ResumeUploader from '@/components/resume/ResumeUploader.vue'
import ResumeList from '@/components/resume/ResumeList.vue'
import { getResumeList, deleteResume, type ResumeData } from '@/api/resume'

const resumes = ref<ResumeData[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentResume = ref<ResumeData | null>(null)

const loadResumes = async () => {
  loading.value = true
  try {
    const result = await getResumeList()
    resumes.value = result.data || []
  } finally {
    loading.value = false
  }
}

const handleUploadSuccess = (data: ResumeData) => {
  resumes.value.unshift(data)
}

const handleView = (resume: ResumeData) => {
  currentResume.value = resume
  dialogVisible.value = true
}

const handleDelete = async (id: string) => {
  await ElMessageBox.confirm('确定删除这份简历？', '提示')
  await deleteResume(id)
  ElMessage.success('删除成功')
  resumes.value = resumes.value.filter(r => r.id !== id)
}

onMounted(loadResumes)
</script>
```

**Step 4: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): 添加简历解析页面"
```

---

### Task 5.5: 智能问答页面

**Files:**
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/components/chat/ChatWindow.vue`
- Create: `frontend/src/components/chat/MessageBubble.vue`

**Step 1: 创建 MessageBubble.vue**

```vue
<template>
  <div
    class="flex mb-4"
    :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[70%] px-4 py-2 rounded-lg"
      :class="message.role === 'user'
        ? 'bg-primary text-white'
        : 'bg-white border shadow-sm'"
    >
      <div class="whitespace-pre-wrap">{{ message.content }}</div>
      <div
        v-if="metrics"
        class="text-xs mt-1 opacity-60"
      >
        首字 {{ metrics.first_token_ms }}ms / 总计 {{ metrics.total_ms }}ms
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage, StreamChunk } from '@/api/chat'

defineProps<{
  message: ChatMessage
  metrics?: StreamChunk['metrics']
}>()
</script>
```

**Step 2: 创建 ChatWindow.vue**

```vue
<template>
  <div class="flex flex-col h-full">
    <!-- 消息列表 -->
    <div ref="messagesRef" class="flex-1 overflow-y-auto p-4 bg-gray-50">
      <MessageBubble
        v-for="(msg, idx) in messages"
        :key="idx"
        :message="msg"
        :metrics="idx === messages.length - 1 ? lastMetrics : undefined"
      />

      <!-- 加载中 -->
      <div v-if="loading" class="flex justify-start mb-4">
        <div class="bg-white border shadow-sm px-4 py-2 rounded-lg">
          <span class="typing-dots">正在思考</span>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="p-4 bg-white border-t">
      <div class="flex gap-2">
        <el-input
          v-model="inputText"
          placeholder="输入问题..."
          @keyup.enter="handleSend"
          :disabled="loading"
        />
        <el-button
          type="primary"
          @click="handleSend"
          :loading="loading"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { chatStream, type ChatMessage, type StreamChunk } from '@/api/chat'

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const sessionId = ref<string>()
const lastMetrics = ref<StreamChunk['metrics']>()
const messagesRef = ref<HTMLElement>()

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const handleSend = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  // 添加助手消息占位
  const assistantIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

  try {
    for await (const chunk of chatStream(text, sessionId.value)) {
      if (chunk.type === 'text') {
        messages.value[assistantIdx].content += chunk.content || ''
        scrollToBottom()
      } else if (chunk.type === 'done') {
        lastMetrics.value = chunk.metrics
        sessionId.value = chunk.metrics?.session_id
      }
    }
  } catch (e) {
    messages.value[assistantIdx].content = '抱歉，发生了错误，请重试。'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.typing-dots::after {
  content: '...';
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}
</style>
```

**Step 3: 创建 ChatView.vue**

```vue
<template>
  <div class="h-[calc(100vh-100px)]">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-2xl font-bold">智能问答</h1>
      <el-button @click="clearChat">新对话</el-button>
    </div>

    <el-card class="h-[calc(100%-60px)]" body-style="height: 100%; padding: 0;">
      <ChatWindow ref="chatWindowRef" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'

const chatWindowRef = ref()

const clearChat = () => {
  // 刷新页面简单实现新对话
  location.reload()
}
</script>
```

**Step 4: 创建组件目录**

```bash
mkdir -p frontend/src/components/chat
mkdir -p frontend/src/components/resume
```

**Step 5: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): 添加智能问答页面"
```

---

## Phase 6: 集成测试与收尾

### Task 6.1: ES 索引初始化脚本

**Files:**
- Create: `backend/scripts/init_es.py`

**Step 1: 创建 init_es.py**

```python
#!/usr/bin/env python3
"""初始化 Elasticsearch 索引"""

from elasticsearch import Elasticsearch

ES_HOST = "http://localhost:9200"

RESUMES_INDEX = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "ik_smart_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_smart"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "file_name": {"type": "keyword"},
            "file_type": {"type": "keyword"},
            "raw_text": {"type": "text"},
            "basic_info": {
                "properties": {
                    "name": {"type": "keyword"},
                    "phone": {"type": "keyword"},
                    "email": {"type": "keyword"},
                    "age": {"type": "integer"},
                    "gender": {"type": "keyword"}
                }
            },
            "education": {"type": "nested"},
            "experience": {"type": "nested"},
            "skills": {
                "properties": {
                    "hard_skills": {"type": "keyword"},
                    "soft_skills": {"type": "keyword"}
                }
            },
            "warnings": {"type": "nested"},
            "match_score": {"type": "float"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    }
}

KNOWLEDGE_INDEX = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text"},
            "content": {"type": "text"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "source": {"type": "keyword"},
            "created_at": {"type": "date"}
        }
    }
}

def main():
    es = Elasticsearch(hosts=[ES_HOST])

    if not es.ping():
        print("❌ 无法连接到 Elasticsearch")
        return

    print("✅ Elasticsearch 连接成功")

    # 创建 resumes 索引
    if not es.indices.exists(index="resumes"):
        es.indices.create(index="resumes", body=RESUMES_INDEX)
        print("✅ 创建索引: resumes")
    else:
        print("ℹ️ 索引已存在: resumes")

    # 创建 knowledge_base 索引
    if not es.indices.exists(index="knowledge_base"):
        es.indices.create(index="knowledge_base", body=KNOWLEDGE_INDEX)
        print("✅ 创建索引: knowledge_base")
    else:
        print("ℹ️ 索引已存在: knowledge_base")

    print("\n🎉 初始化完成!")

if __name__ == "__main__":
    main()
```

**Step 2: 运行初始化**

```bash
cd backend && uv run python scripts/init_es.py
```

**Step 3: 提交**

```bash
git add backend/scripts/
git commit -m "feat(backend): 添加ES索引初始化脚本"
```

---

### Task 6.2: 环境变量和启动脚本

**Files:**
- Create: `backend/.env`
- Create: `frontend/.env`
- Create: `scripts/start-dev.sh`

**Step 1: 创建 backend/.env**

```env
# Elasticsearch
ES_HOST=localhost
ES_PORT=9200

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 阿里百炼 (替换为真实Key)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# JWT
JWT_SECRET=dev-secret-change-in-production

# App
DEBUG=true
```

**Step 2: 创建 frontend/.env**

```env
VITE_API_BASE_URL=http://localhost:8000
```

**Step 3: 创建 scripts/start-dev.sh**

```bash
#!/bin/bash

echo "🚀 启动开发环境..."

# 启动基础设施
echo "📦 启动 Elasticsearch 和 Redis..."
docker-compose up -d elasticsearch redis

# 等待ES启动
echo "⏳ 等待 Elasticsearch 启动..."
sleep 10

# 初始化ES索引
echo "📊 初始化 ES 索引..."
cd backend && uv run python scripts/init_es.py
cd ..

# 启动后端
echo "🔧 启动后端服务..."
cd backend && uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# 启动前端
echo "🎨 启动前端服务..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 开发环境已启动!"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待退出
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

**Step 4: 添加执行权限**

```bash
chmod +x scripts/start-dev.sh
```

**Step 5: 提交**

```bash
git add .env* scripts/
git commit -m "feat: 添加环境变量和启动脚本"
```

---

### Task 6.3: 创建测试简历样本

**Files:**
- Create: `tests/samples/resume_sample.txt`

**Step 1: 创建测试简历**

```
# tests/samples/resume_sample.txt

张三
电话：13812345678
邮箱：zhangsan@example.com
性别：男
年龄：28

【教育背景】
2014-2018  北京大学  计算机科学与技术  本科

【工作经历】
2018-2020  阿里巴巴  后端开发工程师
- 负责电商平台订单系统开发
- 使用Java/Spring Boot开发微服务
- 优化数据库查询，提升系统性能50%

2020-至今  字节跳动  高级开发工程师
- 负责推荐系统后端开发
- 使用Go语言开发高并发服务
- 带领5人小团队完成核心模块重构

【专业技能】
- 编程语言：Python、Java、Go、JavaScript
- 框架：Spring Boot、FastAPI、Vue.js
- 数据库：MySQL、Redis、Elasticsearch
- 其他：Docker、Kubernetes、CI/CD

【求职意向】
期望职位：技术专家
期望薪资：40-50K
期望城市：北京
```

**Step 2: 提交**

```bash
mkdir -p tests/samples
git add tests/
git commit -m "test: 添加测试简历样本"
```

---

### Task 6.4: 端到端验证

**Step 1: 启动全部服务**

```bash
./scripts/start-dev.sh
```

**Step 2: 验证后端API**

```bash
# 健康检查
curl http://localhost:8000/health

# 上传简历测试
curl -X POST http://localhost:8000/api/resume/upload \
  -F "file=@tests/samples/resume_sample.txt"

# 获取简历列表
curl http://localhost:8000/api/resume/list

# 测试问答 (SSE)
curl -N -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下自己"}'
```

**Step 3: 验证前端页面**

```
1. 访问 http://localhost:5173
2. 点击「简历解析」，上传测试简历
3. 验证简历列表显示
4. 点击「智能问答」，发送测试消息
5. 验证流式响应效果
```

**Step 4: 完成验证后提交**

```bash
git add .
git commit -m "chore: 完成端到端验证"
```

---

### Task 6.5: 创建 README

**Files:**
- Create: `README.md`

**Step 1: 创建 README.md**

```markdown
# 智能简历解析与流式问答助手

> POC 验证项目

## 功能特性

- 📄 **简历解析**: 支持 PDF/Word/TXT/图片 多格式简历解析
- 💬 **智能问答**: 基于 RAG 的流式问答，支持卡片展示
- 🔍 **结构化提取**: 自动提取姓名、教育、工作经历等信息
- ⚠️ **风险检测**: 识别简历中的虚假信息和逻辑矛盾

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Element Plus + TailwindCSS |
| 后端 | FastAPI + Python 3.11 |
| 数据库 | Elasticsearch 8.17 |
| 缓存 | Redis |
| 大模型 | Qwen3-32B (阿里百炼) |

## 快速开始

### 1. 环境准备

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- uv (Python 包管理)

### 2. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env，填入阿里百炼 API Key
```

### 3. 启动服务

```bash
./scripts/start-dev.sh
```

### 4. 访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 项目结构

```
├── frontend/          # Vue3 前端
├── backend/           # FastAPI 后端
├── scripts/           # 启动脚本
├── tests/             # 测试文件
└── docker-compose.yml # Docker 配置
```

## API 接口

### 简历解析
- `POST /api/resume/upload` - 上传解析简历
- `GET /api/resume/list` - 获取简历列表
- `GET /api/resume/{id}` - 获取简历详情

### 智能问答
- `POST /api/chat/message` - 发送消息 (SSE)
- `POST /api/chat/session` - 创建会话
- `GET /api/chat/history/{id}` - 获取历史

## License

MIT
```

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 添加项目README"
```

---

## 计划总结

| Phase | 任务数 | 内容 |
|-------|--------|------|
| Phase 1 | 3 | 项目初始化与基础设施 |
| Phase 2 | 3 | 后端核心服务 |
| Phase 3 | 4 | 简历解析模块 |
| Phase 4 | 4 | 智能问答模块 |
| Phase 5 | 5 | 前端开发 |
| Phase 6 | 5 | 集成测试与收尾 |
| **总计** | **24** | |

---

**执行建议:**
1. 按 Phase 顺序执行，每个 Task 完成后立即提交
2. Phase 1-2 完成后验证基础设施正常
3. Phase 3-4 完成后验证后端 API 正常
4. Phase 5 完成后进行端到端测试
