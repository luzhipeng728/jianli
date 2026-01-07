# AI 线上面试系统设计文档

## 1. 概述

### 1.1 项目目标
开发一套AI驱动的线上面试系统，支持候选人独立完成笔试+语音面试，HR事后查看评估报告。

### 1.2 核心特性
- **双智能体协作**：面试官Agent + 控场Agent
- **笔试模块**：AI根据JD+简历实时生成客观题
- **语音面试**：基于阿里云ASR/TTS的纯语音对话
- **智能评估**：多维度评分+详细分析报告

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           前端应用                                   │
├────────────────────────────┬────────────────────────────────────────┤
│      HR管理端 (现有项目)     │        候选人面试端 (独立子项目)         │
│  - JD管理                   │  - 身份验证                             │
│  - 发起面试邀请              │  - 笔试答题                             │
│  - 查看面试记录/回放         │  - 语音面试                             │
│  - 查看评估报告              │  - 状态展示                             │
└─────────────┬──────────────┴──────────────────┬─────────────────────┘
              │                                  │
              ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI 后端                                  │
├─────────────────┬───────────────────┬───────────────────────────────┤
│   JD管理 API    │   面试会话 API     │      WebSocket 网关            │
│   /api/jd/*     │   /api/interview/* │   /ws/interview/{token}       │
└────────┬────────┴─────────┬─────────┴──────────────┬────────────────┘
         │                  │                        │
         ▼                  ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LangChain Agent 层                               │
├─────────────────────────────┬───────────────────────────────────────┤
│       面试官智能体           │            控场智能体                   │
│  InterviewerAgent           │       ControllerAgent                  │
│  - 根据JD+简历生成题目        │  - 异步监控对话质量                     │
│  - 语音面试提问/追问          │  - 生成话题引导指令                     │
│  - 评估候选人回答             │  - 判断面试结束时机                     │
└─────────────────────────────┴───────────────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│   Redis           │   阿里云语音服务      │   Elasticsearch          │
│   - 面试状态       │   - ASR 语音识别      │   - JD存储               │
│   - Agent上下文    │   - TTS 语音合成      │   - 面试记录             │
│   - 控场指令队列   │                       │   - 评估报告             │
└───────────────────┴───────────────────────┴──────────────────────────┘
```

---

## 3. 数据模型

### 3.1 岗位描述 (JD)

```python
class JobDescription(BaseModel):
    id: str                          # UUID
    title: str                       # 岗位名称
    department: str                  # 部门
    description: str                 # 岗位描述
    requirements: list[str]          # 任职要求
    required_skills: list[str]       # 必需技能
    preferred_skills: list[str]      # 加分技能

    interview_config: InterviewConfig

    created_at: datetime
    updated_at: datetime
    created_by: str                  # 创建人

class InterviewConfig(BaseModel):
    written_question_count: int = 5          # 笔试题数量
    voice_max_duration: int = 30             # 语音面试最大时长(分钟)
    focus_areas: list[str] = []              # 重点考察方向
    difficulty: str = "medium"               # easy/medium/hard
```

### 3.2 面试会话

```python
class InterviewSession(BaseModel):
    id: str                          # UUID
    token: str                       # 面试链接token (用于URL)

    resume_id: str                   # 关联简历ID
    jd_id: str                       # 关联JD ID

    status: InterviewStatus          # 面试状态

    # 笔试部分
    written_test: WrittenTest | None

    # 语音面试部分
    voice_interview: VoiceInterview | None

    # 评估报告
    evaluation: Evaluation | None

    created_at: datetime
    started_at: datetime | None      # 候选人开始时间
    completed_at: datetime | None    # 完成时间
    cancelled_at: datetime | None    # 取消时间
    cancelled_reason: str | None

class InterviewStatus(str, Enum):
    PENDING = "pending"              # 等待候选人
    WRITTEN_TEST = "written_test"    # 笔试中
    VOICE_INTERVIEW = "voice"        # 语音面试中
    COMPLETED = "completed"          # 已完成
    CANCELLED = "cancelled"          # 已取消
```

### 3.3 笔试数据

```python
class WrittenTest(BaseModel):
    questions: list[Question]
    answers: list[Answer]
    score: float                     # 得分 0-100
    started_at: datetime
    completed_at: datetime | None

class Question(BaseModel):
    id: str
    type: QuestionType               # single/multiple/judgment
    content: str                     # 题目内容
    options: list[str]               # 选项 A/B/C/D
    correct_answer: str | list[str]  # 正确答案
    explanation: str                 # 解析
    points: int                      # 分值

class QuestionType(str, Enum):
    SINGLE = "single"                # 单选
    MULTIPLE = "multiple"            # 多选
    JUDGMENT = "judgment"            # 判断

class Answer(BaseModel):
    question_id: str
    answer: str | list[str]
    is_correct: bool
    time_spent: int                  # 答题耗时(秒)
```

### 3.4 语音面试数据

```python
class VoiceInterview(BaseModel):
    started_at: datetime
    ended_at: datetime | None
    duration: int                    # 时长(秒)

    transcript: list[TranscriptMessage]  # 对话记录
    audio_url: str | None            # 完整录音URL

    end_reason: str                  # 结束原因: completed/timeout/error

class TranscriptMessage(BaseModel):
    role: str                        # interviewer/candidate
    content: str                     # 文字内容
    audio_url: str | None            # 单句录音URL
    timestamp: datetime
    duration: float                  # 时长(秒)
```

### 3.5 评估报告

```python
class Evaluation(BaseModel):
    overall_score: int               # 综合评分 0-100
    recommendation: str              # strongly_recommend/recommend/neutral/not_recommend

    dimensions: list[DimensionScore]

    highlights: list[str]            # 亮点
    concerns: list[str]              # 风险点

    summary: str                     # AI总结
    detailed_analysis: str           # 详细分析

    generated_at: datetime

class DimensionScore(BaseModel):
    name: str                        # 维度名称
    score: int                       # 0-100
    weight: float                    # 权重
    analysis: str                    # 该维度分析

# 默认评估维度
DEFAULT_DIMENSIONS = [
    "专业能力",
    "沟通表达",
    "逻辑思维",
    "学习能力",
    "岗位匹配度"
]
```

### 3.6 Redis 键设计

```python
# 面试状态
f"interview:{session_id}:status"      # InterviewStatus

# Agent 上下文 (对话历史、候选人信息等)
f"interview:{session_id}:context"     # JSON

# 控场Agent指令队列 (List)
f"interview:{session_id}:directives"  # List[ControllerDirective]

# 当前语音状态
f"interview:{session_id}:voice_state" # speaking/listening/processing

# 实时转写缓冲
f"interview:{session_id}:asr_buffer"  # 当前ASR识别结果
```

---

## 4. 双智能体设计

### 4.1 面试官智能体 (InterviewerAgent)

**职责**：
- 根据JD+简历生成笔试题目
- 进行语音面试提问
- 根据回答进行追问/深挖
- 评估候选人表现

**System Prompt 模板**：

```
你是一位专业的面试官，正在面试 {candidate_name}，应聘 {job_title} 岗位。

## 候选人简历摘要
{resume_summary}

## 岗位要求
{jd_summary}

## 面试指导
- 根据简历和岗位要求进行针对性提问
- 每次只问一个问题，等待回答后再继续
- 适当追问以深入了解候选人能力
- 保持专业、友好的面试氛围
- 注意倾听，不要打断候选人

## 控场指令
{controller_directives}

## 对话历史
{conversation_history}
```

**核心方法**：

```python
class InterviewerAgent:
    async def generate_questions(self, jd: JobDescription, resume: ResumeData) -> list[Question]:
        """根据JD和简历生成笔试题目"""
        pass

    async def ask_question(self, context: InterviewContext) -> str:
        """生成下一个面试问题"""
        pass

    async def evaluate_answer(self, question: str, answer: str) -> AnswerEvaluation:
        """评估候选人回答"""
        pass

    async def generate_evaluation(self, session: InterviewSession) -> Evaluation:
        """生成最终评估报告"""
        pass
```

### 4.2 控场智能体 (ControllerAgent)

**职责**：
- 异步监控对话质量和进度
- 生成话题引导指令（静默发给面试官Agent）
- 判断面试是否可以结束
- 监控异常情况（超时、跑题等）

**System Prompt 模板**：

```
你是面试控场助手，负责监控面试进度和质量。你的指令只发给面试官，候选人不会看到。

## 岗位要求重点
{focus_areas}

## 当前面试进度
- 已进行时间: {elapsed_time}
- 已问问题数: {question_count}
- 已覆盖话题: {covered_topics}

## 对话历史
{conversation_history}

## 你的任务
1. 判断当前面试是否需要引导
2. 如果需要，生成简短的引导指令
3. 判断面试是否可以结束

## 输出格式
{
  "should_guide": bool,
  "directive": "引导指令内容(如有)",
  "should_end": bool,
  "end_reason": "结束原因(如有)"
}
```

**核心方法**：

```python
class ControllerAgent:
    async def analyze(self, context: InterviewContext) -> ControllerDecision:
        """分析当前面试状态，返回决策"""
        pass

    async def run_loop(self, session_id: str):
        """异步监控循环，定期分析并发送指令"""
        while session_active:
            context = await get_context(session_id)
            decision = await self.analyze(context)

            if decision.should_guide:
                await push_directive(session_id, decision.directive)

            if decision.should_end:
                await trigger_end(session_id, decision.end_reason)
                break

            await asyncio.sleep(10)  # 每10秒分析一次
```

### 4.3 智能体协作流程

```
                    ┌─────────────────┐
                    │  面试开始        │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    │
┌───────────────┐    ┌───────────────┐           │
│ 面试官Agent   │    │  控场Agent    │           │
│               │    │  (异步运行)   │           │
│ 1.提问        │    │               │           │
│   ↓           │    │ 1.监控对话    │           │
│ 2.等待回答    │◄───│ 2.发送指令    │           │
│   ↓           │    │ 3.判断结束    │           │
│ 3.追问/下一题 │    │               │           │
└───────┬───────┘    └───────┬───────┘           │
        │                    │                    │
        │                    │ (结束信号)         │
        │                    ▼                    │
        │            ┌───────────────┐           │
        └───────────►│  面试结束     │◄──────────┘
                     │  生成报告     │   (最大时长)
                     └───────────────┘
```

---

## 5. 阿里云语音集成

### 5.1 服务选型

| 服务 | 用途 | 接口 |
|------|------|------|
| 语音识别 (ASR) | 候选人语音转文字 | 实时语音识别 WebSocket |
| 语音合成 (TTS) | 面试官问题转语音 | 流式语音合成 |

### 5.2 语音识别流程

```
候选人麦克风 → 前端采集音频 → WebSocket → 后端 → 阿里云ASR
                                                    ↓
                                              实时转写结果
                                                    ↓
                                            面试官Agent处理
```

### 5.3 语音合成流程

```
面试官Agent输出文字 → 阿里云TTS → 流式音频 → WebSocket → 前端播放
```

### 5.4 WebSocket 消息协议

```typescript
// 前端 → 后端
interface ClientMessage {
  type: "audio" | "control"
  // audio: 音频数据 (base64)
  audio?: string
  // control: 控制指令
  action?: "start" | "stop" | "pause" | "resume"
}

// 后端 → 前端
interface ServerMessage {
  type: "transcript" | "audio" | "status" | "question" | "end"

  // transcript: ASR结果
  text?: string
  is_final?: boolean

  // audio: TTS音频
  audio?: string  // base64

  // status: 状态更新
  status?: "listening" | "processing" | "speaking"

  // question: 面试官问题
  question?: string

  // end: 面试结束
  reason?: string
  evaluation_ready?: boolean
}
```

---

## 6. API 设计

### 6.1 JD 管理

```
POST   /api/jd                    创建JD
GET    /api/jd                    JD列表
GET    /api/jd/{id}               JD详情
PUT    /api/jd/{id}               更新JD
DELETE /api/jd/{id}               删除JD
```

### 6.2 面试管理

```
POST   /api/interview/create      创建面试邀请
GET    /api/interview/list        面试列表(HR端)
GET    /api/interview/{id}        面试详情
DELETE /api/interview/{id}        取消面试

GET    /api/interview/by-token/{token}   根据token获取面试信息(候选人端)
POST   /api/interview/{id}/start         开始面试
GET    /api/interview/{id}/evaluation    获取评估报告
GET    /api/interview/{id}/recording     获取面试录音
```

### 6.3 WebSocket

```
WS     /ws/interview/{token}      面试语音通道
```

---

## 7. 前端页面设计

### 7.1 HR管理端 (现有项目扩展)

**新增页面**：

1. **JD管理页** `/jd`
   - JD列表
   - 创建/编辑JD表单
   - 面试配置

2. **面试管理页** `/interviews`
   - 面试列表（状态筛选）
   - 面试详情/回放
   - 评估报告查看

3. **候选人卡片弹窗** (修复现有bug)
   - 显示候选人详情
   - "发起面试"按钮
   - 选择JD
   - 生成面试链接

### 7.2 候选人面试端 (独立子项目)

**技术栈**：Vue 3 + Vite + TypeScript + TailwindCSS

**页面**：

1. **面试入口页** `/interview/{token}`
   - 验证token有效性
   - 显示岗位信息
   - 设备检测（麦克风权限）
   - "开始面试"按钮

2. **笔试页** `/interview/{token}/written`
   - 题目卡片（流式显示）
   - 选项选择
   - 计时器
   - 提交按钮

3. **语音面试页** `/interview/{token}/voice`
   - 面试官头像/状态
   - 实时转写显示
   - 录音状态指示
   - 静音/结束按钮

4. **完成页** `/interview/{token}/complete`
   - 面试完成提示
   - 感谢语

---

## 8. 实现计划

### Phase 1: 基础设施
- [ ] 创建候选人面试端子项目
- [ ] Redis 集成
- [ ] 阿里云语音服务集成
- [ ] WebSocket 网关

### Phase 2: JD管理
- [ ] JD数据模型和ES索引
- [ ] JD CRUD API
- [ ] JD管理前端页面

### Phase 3: 面试流程
- [ ] 面试会话数据模型
- [ ] 创建面试/生成链接
- [ ] 候选人入口页
- [ ] 修复聊天页候选人卡片点击

### Phase 4: 笔试模块
- [ ] 题目生成Agent
- [ ] 笔试答题页面
- [ ] 自动评分

### Phase 5: 语音面试
- [ ] 面试官Agent
- [ ] 控场Agent
- [ ] 语音识别集成
- [ ] 语音合成集成
- [ ] 语音面试页面

### Phase 6: 评估报告
- [ ] 评估生成Agent
- [ ] 评估报告页面
- [ ] 面试回放功能

---

## 9. 技术要点

### 9.1 并发处理
- 使用 asyncio 处理多个面试会话
- 控场Agent独立协程运行
- Redis pub/sub 用于Agent间通信

### 9.2 音频处理
- 前端使用 MediaRecorder API 采集音频
- PCM 16kHz 16bit 格式
- 分片传输（每200ms一个包）

### 9.3 状态管理
- 所有面试状态存储在 Redis
- 定期持久化到 Elasticsearch
- 支持断线重连恢复

### 9.4 错误处理
- WebSocket 断线自动重连
- ASR/TTS 失败降级处理
- 面试中断恢复机制

---

## 10. 附录

### 10.1 评估维度说明

| 维度 | 权重 | 评估要点 |
|------|------|----------|
| 专业能力 | 30% | 技术深度、问题解决能力 |
| 沟通表达 | 20% | 表达清晰度、逻辑性 |
| 逻辑思维 | 20% | 分析问题、推理能力 |
| 学习能力 | 15% | 知识广度、学习态度 |
| 岗位匹配度 | 15% | 经验匹配、意愿度 |

### 10.2 笔试题型示例

**单选题**：
```json
{
  "type": "single",
  "content": "在Python中，以下哪个是不可变数据类型？",
  "options": ["A. list", "B. dict", "C. tuple", "D. set"],
  "correct_answer": "C",
  "explanation": "tuple是不可变类型，创建后不能修改"
}
```

**多选题**：
```json
{
  "type": "multiple",
  "content": "以下哪些是RESTful API的设计原则？",
  "options": ["A. 使用HTTP动词", "B. 无状态", "C. 使用WebSocket", "D. 资源URI"],
  "correct_answer": ["A", "B", "D"],
  "explanation": "RESTful强调HTTP动词、无状态和资源URI"
}
```

**判断题**：
```json
{
  "type": "judgment",
  "content": "Redis是一个关系型数据库",
  "options": ["A. 正确", "B. 错误"],
  "correct_answer": "B",
  "explanation": "Redis是键值型NoSQL数据库"
}
```
