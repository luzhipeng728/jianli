# Redis 使用指南

本文档说明如何在项目中使用 Redis 客户端和面试状态管理功能。

## 目录

- [安装依赖](#安装依赖)
- [配置](#配置)
- [Redis 客户端](#redis-客户端)
- [面试状态管理](#面试状态管理)
- [测试](#测试)

## 安装依赖

项目已经在 `pyproject.toml` 中配置了 Redis 依赖，安装方式：

```bash
cd backend
pip install -e .
```

## 配置

### 环境变量

在 `.env` 文件中配置 Redis 连接：

```env
REDIS_URL=redis://localhost:6379/0
```

支持的 URL 格式：
- 单机模式: `redis://localhost:6379/0`
- 密码认证: `redis://:password@localhost:6379/0`
- Redis Sentinel: `redis+sentinel://host:26379/mymaster/0`
- Redis Cluster: `redis://node1:6379,node2:6379,node3:6379/0`

### 连接池配置

默认连接池配置：
- 最大连接数: 50
- 编码: UTF-8
- 响应解码: 自动解码为字符串

## Redis 客户端

### 基础用法

```python
from app.services.redis_client import get_redis_client

# 获取客户端实例（单例模式）
redis = await get_redis_client()

# 字符串操作
await redis.set("key", "value", ex=3600)  # 设置值，1小时过期
value = await redis.get("key")  # 获取值
await redis.delete("key")  # 删除键

# JSON 操作
data = {"name": "张三", "age": 25}
await redis.set_json("user:001", data, ex=3600)
user = await redis.get_json("user:001")

# 列表操作
await redis.rpush("queue", "task1", "task2", "task3")
task = await redis.lpop("queue")  # 从队列头部弹出

# 哈希表操作
await redis.hset("user:001:profile", "name", "张三")
await redis.hset("user:001:profile", "age", "25")
profile = await redis.hgetall("user:001:profile")

# 发布订阅
await redis.publish("chat:room1", "Hello, World!")
pubsub = await redis.subscribe("chat:room1")
async for message in pubsub.listen():
    print(message)
```

### 依赖注入（FastAPI）

```python
from fastapi import Depends
from app.services.redis_client import get_redis_client, RedisClient

@app.get("/api/test")
async def test_endpoint(redis: RedisClient = Depends(get_redis_client)):
    await redis.set("test", "value")
    value = await redis.get("test")
    return {"value": value}
```

## 面试状态管理

### 创建面试会话

```python
from app.services.interview_state import (
    get_interview_state_manager,
    InterviewPhase
)

manager = get_interview_state_manager()

# 创建会话
context = await manager.create_session(
    session_id="interview_001",
    candidate_id="candidate_001",
    resume_id="resume_001",
    job_position="Python后端工程师",
    config={
        "duration": 60,  # 面试时长（分钟）
        "difficulty": "medium",
        "focus_areas": ["Python", "FastAPI", "数据库"]
    },
    ttl=7200  # 2小时过期
)
```

### 管理面试阶段

```python
# 切换阶段
await manager.change_phase("interview_001", InterviewPhase.TECHNICAL)

# 获取当前会话
context = await manager.get_session("interview_001")
print(f"当前阶段: {context.current_phase}")

# 添加对话记录
await manager.add_conversation(
    session_id="interview_001",
    role="interviewer",
    content="请介绍一下你的项目经验",
    metadata={"phase": "technical", "timestamp": "2024-01-01T10:00:00"}
)

await manager.add_conversation(
    session_id="interview_001",
    role="candidate",
    content="我参与开发了一个基于FastAPI的微服务项目...",
    metadata={"phase": "technical", "timestamp": "2024-01-01T10:01:00"}
)

# 添加评估笔记
await manager.add_evaluation_note(
    session_id="interview_001",
    category="技术能力",
    score=8.5,
    note="候选人对FastAPI有深入理解，能够清晰地解释异步编程的概念"
)
```

### Agent 状态管理

```python
from app.services.interview_state import AgentState

# 创建面试官 Agent 状态
interviewer = AgentState(
    agent_id="interviewer_001",
    agent_type="interviewer",
    status="thinking",
    current_task="准备技术问题",
    memory={
        "last_topic": "异步编程",
        "question_count": 3,
        "candidate_level": "intermediate"
    }
)

await manager.set_agent_state("interview_001", interviewer)

# 更新 Agent 状态
await manager.update_agent_status(
    session_id="interview_001",
    agent_id="interviewer_001",
    status="speaking",
    current_task="提问技术问题"
)

# 获取 Agent 状态
state = await manager.get_agent_state("interview_001", "interviewer_001")
print(f"Agent状态: {state.status}, 任务: {state.current_task}")
```

### 控场指令队列

```python
from app.services.interview_state import CommandType, ControlCommand

# 推送阶段切换指令
await manager.push_phase_change_command(
    session_id="interview_001",
    new_phase=InterviewPhase.BEHAVIORAL,
    reason="技术问答完成"
)

# 推送中断指令（高优先级）
await manager.push_interrupt_command(
    session_id="interview_001",
    reason="候选人网络断开",
    action="pause"
)

# 推送提示指令
await manager.push_hint_command(
    session_id="interview_001",
    hint_text="注意控制时间，还剩10分钟",
    target_agent="interviewer_001"
)

# 推送结束面试指令
await manager.push_end_interview_command(
    session_id="interview_001",
    reason="面试时间到"
)

# 弹出指令（FIFO顺序）
while True:
    command = await manager.pop_command("interview_001")
    if command is None:
        break

    if command.command_type == CommandType.PHASE_CHANGE:
        new_phase = command.payload["new_phase"]
        await manager.change_phase("interview_001", new_phase)
    elif command.command_type == CommandType.INTERRUPT:
        # 处理中断
        pass
    elif command.command_type == CommandType.END_INTERVIEW:
        # 结束面试
        break
```

### 面试会话完整流程示例

```python
async def conduct_interview():
    """完整的面试流程示例"""
    manager = get_interview_state_manager()
    session_id = "interview_001"

    # 1. 创建会话
    await manager.create_session(
        session_id=session_id,
        candidate_id="candidate_001",
        resume_id="resume_001",
        job_position="Python后端工程师"
    )

    # 2. 初始化 Agents
    interviewer = AgentState(
        agent_id="interviewer_001",
        agent_type="interviewer",
        status="idle"
    )
    evaluator = AgentState(
        agent_id="evaluator_001",
        agent_type="evaluator",
        status="idle"
    )

    await manager.set_agent_state(session_id, interviewer)
    await manager.set_agent_state(session_id, evaluator)

    # 3. 开始面试 - 自我介绍阶段
    await manager.change_phase(session_id, InterviewPhase.INTRO)
    await manager.add_conversation(
        session_id, "interviewer",
        "您好，请先做个自我介绍"
    )

    # 4. 技术面试阶段
    await manager.change_phase(session_id, InterviewPhase.TECHNICAL)
    await manager.add_conversation(
        session_id, "interviewer",
        "请解释一下Python的GIL"
    )
    await manager.add_conversation(
        session_id, "candidate",
        "GIL是全局解释器锁..."
    )

    # 5. 实时评估
    await manager.add_evaluation_note(
        session_id,
        category="技术深度",
        score=8.0,
        note="对GIL有清晰的理解"
    )

    # 6. 结束面试
    await manager.change_phase(session_id, InterviewPhase.COMPLETED)

    # 7. 获取完整的面试数据
    context = await manager.get_session(session_id)
    return {
        "session_id": context.session_id,
        "candidate": context.candidate_id,
        "position": context.job_position,
        "conversations": len(context.conversation_history),
        "evaluations": context.evaluation_notes,
        "duration": (context.end_time - context.start_time).seconds
            if context.end_time else None
    }
```

## 测试

运行测试脚本验证 Redis 功能：

```bash
cd backend
python3 test_redis.py
```

测试内容包括：
1. Redis 基础操作（字符串、JSON、列表）
2. 面试会话管理
3. Agent 状态管理
4. 控场指令队列

## 性能建议

### 1. 连接复用

Redis 客户端使用单例模式和连接池，自动复用连接。不要频繁创建新的客户端实例。

```python
# 好的做法
redis = await get_redis_client()
await redis.set("key1", "value1")
await redis.set("key2", "value2")

# 不好的做法（创建多个实例）
redis1 = await get_redis_client()
await redis1.set("key1", "value1")
redis2 = await get_redis_client()
await redis2.set("key2", "value2")
```

### 2. 批量操作

使用批量操作减少网络往返：

```python
# 批量设置哈希字段
await redis.hmset("user:001", {
    "name": "张三",
    "age": "25",
    "city": "北京"
})

# 批量推入列表
await redis.rpush("queue", "task1", "task2", "task3")
```

### 3. 设置过期时间

为临时数据设置合理的 TTL，避免内存泄漏：

```python
# 面试会话2小时过期
await manager.create_session(..., ttl=7200)

# Agent状态1小时过期
await manager.set_agent_state(..., ttl=3600)
```

### 4. 键命名规范

使用统一的键命名规范，便于管理和监控：

```
interview:context:{session_id}          # 面试上下文
interview:agent:{session_id}:{agent_id} # Agent状态
interview:commands:{session_id}         # 控场指令队列
```

## 故障处理

### Redis 连接失败

如果 Redis 连接失败，应用会抛出异常。确保：
1. Redis 服务正在运行
2. 连接配置正确（主机、端口、密码）
3. 网络可达

### 数据丢失

Redis 默认是内存数据库，重启会丢失数据。生产环境建议：
1. 配置 RDB 持久化（定期快照）
2. 配置 AOF 持久化（追加日志）
3. 使用 Redis Sentinel 或 Cluster 提高可用性

### 内存溢出

监控 Redis 内存使用，必要时：
1. 设置 maxmemory 限制
2. 配置淘汰策略（如 allkeys-lru）
3. 为所有键设置合理的 TTL

## 监控和调试

### 查看 Redis 状态

```bash
redis-cli INFO
redis-cli DBSIZE
redis-cli KEYS "interview:*"
```

### 监控命令执行

```bash
redis-cli MONITOR
```

### 慢查询日志

```bash
redis-cli SLOWLOG GET 10
```

## 相关文档

- [Redis 官方文档](https://redis.io/documentation)
- [redis-py 文档](https://redis-py.readthedocs.io/)
- [FastAPI 生命周期管理](https://fastapi.tiangolo.com/advanced/events/)
