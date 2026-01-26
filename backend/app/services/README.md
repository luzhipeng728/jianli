# Services 模块说明

本目录包含后端应用的核心服务模块。

## 模块列表

### 数据存储服务

#### `es_client.py`
Elasticsearch 客户端，用于全文搜索和数据存储。

```python
from app.services.es_client import ESClient

es = ESClient()
es.index_document("resumes", "doc_001", {"name": "张三"})
results = es.search("resumes", {"query": {"match": {"name": "张三"}}})
```

#### `redis_client.py`
Redis 异步客户端（单例模式），支持各种 Redis 数据类型和面试状态管理。

```python
from app.services.redis_client import get_redis_client

redis = await get_redis_client()
await redis.set_json("user:001", {"name": "张三"}, ex=3600)
data = await redis.get_json("user:001")
```

**主要功能：**
- 基础操作：get, set, delete, expire
- JSON 操作：get_json, set_json
- 列表操作：lpush, rpush, lpop, rpop
- 哈希表操作：hget, hset, hgetall
- 发布订阅：publish, subscribe
- 面试状态专用方法：
  - `set_interview_context()` - 存储面试会话上下文
  - `push_control_command()` - 推送控场指令
  - `set_agent_state()` - 设置 Agent 状态

### AI 服务

#### `llm_client.py`
阿里云百炼大模型客户端，支持对话、流式输出、OCR 和文本向量化。

```python
from app.services.llm_client import LLMClient

llm = LLMClient()

# 普通对话
answer = await llm.chat("你好")

# 流式对话
async for chunk in llm.chat_stream("讲个故事"):
    print(chunk, end="", flush=True)

# OCR
text = await llm.ocr(image_data, "image.png")

# 文本向量化
vector = await llm.get_embedding("这是一段文本")
```

### 文件处理服务

#### `file_processor.py`
文件上传和处理服务，支持多种文件格式。

```python
from app.services.file_processor import FileProcessor

processor = FileProcessor()
content = await processor.process_file(file_data, "resume.pdf")
```

**支持的格式：**
- PDF：pdfplumber 提取
- Word：python-docx
- 图片：OCR 识别（PNG, JPG, JPEG, WEBP, BMP）
- 文本：txt, md, json 等

#### `resume_parser.py`
简历解析服务，使用 LLM 提取结构化信息。

```python
from app.services.resume_parser import ResumeParser

parser = ResumeParser()
resume_data = await parser.parse(text_content)
# 返回：姓名、电话、邮箱、教育经历、工作经验、技能等
```

#### `resume_exporter.py`
简历导出服务，支持导出为 PDF、Word 等格式。

### 面试相关服务

#### `interview_state.py`
面试状态管理服务，管理面试会话的完整生命周期。

```python
from app.services.interview_state import (
    get_interview_state_manager,
    InterviewPhase,
    AgentState,
    CommandType
)

manager = get_interview_state_manager()

# 创建会话
context = await manager.create_session(
    session_id="interview_001",
    candidate_id="candidate_001",
    resume_id="resume_001",
    job_position="Python工程师"
)

# 切换阶段
await manager.change_phase("interview_001", InterviewPhase.TECHNICAL)

# 添加对话
await manager.add_conversation(
    "interview_001", "interviewer", "请介绍你的项目"
)

# 推送控场指令
await manager.push_hint_command(
    "interview_001", "注意控制时间"
)
```

**核心功能：**

1. **会话管理**
   - `create_session()` - 创建面试会话
   - `get_session()` - 获取会话信息
   - `update_session()` - 更新会话
   - `change_phase()` - 切换面试阶段

2. **对话管理**
   - `add_conversation()` - 记录对话
   - `add_evaluation_note()` - 添加评估笔记

3. **Agent 管理**
   - `set_agent_state()` - 设置 Agent 状态
   - `get_agent_state()` - 获取 Agent 状态
   - `update_agent_status()` - 更新状态

4. **控场指令**
   - `push_command()` - 推送通用指令
   - `pop_command()` - 弹出指令
   - `push_phase_change_command()` - 阶段切换指令
   - `push_interrupt_command()` - 中断指令
   - `push_hint_command()` - 提示指令
   - `push_end_interview_command()` - 结束指令

**面试阶段枚举：**
- `PREPARING` - 准备中
- `INTRO` - 自我介绍
- `TECHNICAL` - 技术问答
- `BEHAVIORAL` - 行为面试
- `QA` - 候选人提问
- `CLOSING` - 结束阶段
- `COMPLETED` - 已完成

**控场指令类型：**
- `PHASE_CHANGE` - 阶段切换
- `INTERRUPT` - 中断
- `HINT` - 提示
- `TIME_WARNING` - 时间警告
- `END_INTERVIEW` - 结束面试

### 对话服务

#### `chat_engine.py`
对话引擎，处理简历相关的问答。

```python
from app.services.chat_engine import ChatEngine

engine = ChatEngine()
async for chunk in engine.chat_stream(
    question="候选人的工作经验如何？",
    resume_id="resume_001"
):
    print(chunk, end="")
```

### 批处理服务

#### `batch_processor.py`
批量简历处理服务。

#### `task_manager.py`
任务管理器，跟踪批处理任务状态。

#### `background_worker.py`
后台任务处理器，异步执行批处理任务。

### 职位匹配服务

#### `job_matcher.py`
简历与职位匹配服务，评估匹配度。

```python
from app.services.job_matcher import JobMatcher

matcher = JobMatcher()
result = await matcher.match(resume_data, jd_data)
# 返回：匹配分数、优势、不足、建议
```

## 依赖关系

```
main.py
  ├── redis_client.py (启动时初始化)
  ├── background_worker.py (启动时启动)
  └── routes/
      ├── resume.py
      │   ├── file_processor.py
      │   ├── resume_parser.py
      │   └── es_client.py
      ├── chat.py
      │   ├── chat_engine.py
      │   ├── llm_client.py
      │   └── es_client.py
      ├── interview.py
      │   └── interview_state.py
      │       └── redis_client.py
      └── batch.py
          ├── batch_processor.py
          ├── task_manager.py
          └── background_worker.py
```

## 配置

所有服务通过 `app.config.get_settings()` 获取配置，配置项来自环境变量。

```python
from app.config import get_settings

settings = get_settings()
print(settings.redis_url)
print(settings.dashscope_api_key)
```

## 最佳实践

### 1. 单例模式

使用全局单例实例，避免重复创建：

```python
# Redis 客户端
redis = await get_redis_client()

# 面试状态管理器
manager = get_interview_state_manager()
```

### 2. 依赖注入（FastAPI）

在路由中使用依赖注入：

```python
from fastapi import Depends
from app.services.redis_client import get_redis_client, RedisClient

@router.get("/test")
async def test(redis: RedisClient = Depends(get_redis_client)):
    await redis.set("key", "value")
    return {"status": "ok"}
```

### 3. 资源清理

应用会在关闭时自动清理资源（在 `main.py` 的 `lifespan` 中配置）。

### 4. 错误处理

服务层应该抛出明确的异常，由上层路由处理：

```python
try:
    result = await service.process()
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail="Internal server error")
```

## 测试

每个服务模块都应该有对应的测试：

```bash
# 测试 Redis 功能
python3 test_redis.py

# 运行所有测试
pytest tests/
```

## 文档

- [Redis 使用指南](../../REDIS_USAGE.md) - 详细的 Redis 使用文档
- [API 文档](http://localhost:8000/docs) - FastAPI 自动生成的 API 文档
