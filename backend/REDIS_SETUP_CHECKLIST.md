# Redis 配置检查清单

## 配置完成情况

### 1. 依赖配置 ✅

- [x] `pyproject.toml` 中添加了 `redis[hiredis]>=5.0` 依赖
- [x] 包含 hiredis 加速库，提升性能

### 2. 配置文件 ✅

- [x] `app/config.py` 中添加了 `redis_url` 配置项
- [x] `.env` 中添加了 `REDIS_URL=redis://localhost:6379/0`
- [x] 创建了 `.env.example` 模板文件

### 3. Redis 客户端 ✅

**文件路径**: `/root/jianli_final/backend/app/services/redis_client.py`

**特性**:
- [x] 单例模式设计，全局共享一个连接池
- [x] 异步操作支持（基于 redis.asyncio）
- [x] 从环境变量读取配置（REDIS_URL）
- [x] 连接池管理（最大50连接）
- [x] 基础操作：get, set, delete, exists, expire, ttl
- [x] JSON 操作：get_json, set_json
- [x] 列表操作：lpush, rpush, lpop, rpop, lrange, llen
- [x] 哈希操作：hget, hset, hgetall, hmset, hdel
- [x] 集合操作：sadd, srem, smembers, sismember
- [x] 有序集合：zadd, zrange, zrem
- [x] 发布订阅：publish, subscribe
- [x] 面试状态专用方法：
  - `set_interview_context()` - 设置面试上下文
  - `get_interview_context()` - 获取面试上下文
  - `delete_interview_context()` - 删除面试上下文
  - `push_control_command()` - 推送控场指令
  - `pop_control_command()` - 弹出控场指令
  - `get_command_queue_length()` - 获取指令队列长度
  - `clear_command_queue()` - 清空指令队列
  - `set_agent_state()` - 设置 Agent 状态
  - `get_agent_state()` - 获取 Agent 状态
  - `delete_agent_state()` - 删除 Agent 状态

**代码统计**: 316 行

### 4. 面试状态管理 ✅

**文件路径**: `/root/jianli_final/backend/app/services/interview_state.py`

**核心组件**:

#### 数据模型
- [x] `InterviewPhase` - 面试阶段枚举（7个阶段）
- [x] `CommandType` - 控场指令类型枚举（5种类型）
- [x] `InterviewContext` - 面试会话上下文
- [x] `ControlCommand` - 控场指令
- [x] `AgentState` - Agent 状态

#### 管理功能
- [x] **会话管理**:
  - `create_session()` - 创建面试会话
  - `get_session()` - 获取会话信息
  - `update_session()` - 更新会话
  - `delete_session()` - 删除会话
  - `change_phase()` - 切换面试阶段

- [x] **对话管理**:
  - `add_conversation()` - 添加对话记录
  - `add_evaluation_note()` - 添加评估笔记

- [x] **Agent 管理**:
  - `set_agent_state()` - 设置 Agent 状态
  - `get_agent_state()` - 获取 Agent 状态
  - `update_agent_status()` - 更新 Agent 状态
  - `delete_agent_state()` - 删除 Agent 状态

- [x] **控场指令队列**:
  - `push_command()` - 推送通用指令
  - `pop_command()` - 弹出指令
  - `get_command_count()` - 获取队列长度
  - `clear_commands()` - 清空队列
  - `push_phase_change_command()` - 阶段切换指令
  - `push_interrupt_command()` - 中断指令
  - `push_hint_command()` - 提示指令
  - `push_end_interview_command()` - 结束面试指令

**代码统计**: 438 行

### 5. 应用集成 ✅

- [x] 在 `app/main.py` 中的 `lifespan` 函数添加了 Redis 初始化和清理逻辑
- [x] 启动时自动初始化 Redis 连接池
- [x] 关闭时自动清理 Redis 连接

### 6. 文档 ✅

- [x] **REDIS_USAGE.md** - 详细的使用指南（11KB）
  - Redis 客户端使用说明
  - 面试状态管理完整示例
  - 性能建议
  - 故障处理
  - 监控和调试

- [x] **app/services/README.md** - 服务模块总览
  - 所有服务模块的说明
  - 依赖关系图
  - 最佳实践

- [x] **example_usage.py** - 完整的 API 使用示例
  - Redis 基础操作示例路由
  - 面试会话管理示例路由
  - Agent 状态管理示例路由
  - 控场指令队列示例路由
  - 完整流程演示

### 7. 测试 ✅

**文件路径**: `/root/jianli_final/backend/test_redis.py`

- [x] Redis 基础操作测试
- [x] 面试状态管理测试
- [x] Agent 状态管理测试
- [x] 控场指令队列测试

## 部署前检查

### 1. 安装依赖

```bash
cd /root/jianli_final/backend
pip install -e .
```

### 2. 确保 Redis 服务运行

```bash
# 检查 Redis 是否运行
redis-cli ping
# 应该返回: PONG

# 如果未运行，启动 Redis
sudo systemctl start redis
# 或
redis-server
```

### 3. 配置环境变量

检查 `.env` 文件中的 Redis 配置：

```bash
cat .env | grep REDIS
```

应该包含：
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0
```

### 4. 运行测试

```bash
python3 test_redis.py
```

预期输出：
```
=== 测试 Redis 基础操作 ===
✓ 字符串操作: test_value
✓ JSON 操作: {'name': '张三', 'age': 25, 'skills': ['Python', 'FastAPI']}
✓ 列表操作: ['item1', 'item2', 'item3']
✓ 基础操作测试通过

=== 测试面试状态管理 ===
...
所有测试通过！
```

### 5. 启动应用

```bash
uvicorn app.main:app --reload
```

检查启动日志中是否有：
```
[App] 正在初始化 Redis 连接...
[App] Redis 连接初始化完成
```

### 6. 健康检查

```bash
curl http://localhost:8000/health
# 应该返回: {"status":"ok"}
```

## 使用示例

### 快速开始

```python
from app.services.redis_client import get_redis_client
from app.services.interview_state import get_interview_state_manager

# Redis 客户端
redis = await get_redis_client()
await redis.set_json("user:001", {"name": "张三"}, ex=3600)

# 面试状态管理
manager = get_interview_state_manager()
context = await manager.create_session(
    session_id="interview_001",
    candidate_id="candidate_001",
    resume_id="resume_001",
    job_position="Python工程师"
)
```

### FastAPI 路由集成

查看 `example_usage.py` 获取完整的路由示例。

## 性能指标

- **连接池**: 最大 50 并发连接
- **编码**: UTF-8 自动编解码
- **加速库**: hiredis（C 扩展）
- **数据结构**: 支持 String, Hash, List, Set, Sorted Set
- **过期策略**: 自动清理过期数据（Redis TTL）

## 键命名规范

所有面试相关的 Redis 键遵循以下命名规范：

```
interview:context:{session_id}           # 面试上下文
interview:commands:{session_id}          # 控场指令队列
interview:agent:{session_id}:{agent_id}  # Agent 状态
```

自定义键请避免使用 `interview:` 前缀。

## 生产环境建议

1. **持久化配置**
   - 启用 RDB 快照：`save 900 1`
   - 启用 AOF 日志：`appendonly yes`

2. **内存管理**
   - 设置最大内存：`maxmemory 2gb`
   - 淘汰策略：`maxmemory-policy allkeys-lru`

3. **安全配置**
   - 设置密码：`requirepass <strong_password>`
   - 绑定地址：`bind 127.0.0.1`（内网）
   - 更新 REDIS_URL：`redis://:password@localhost:6379/0`

4. **监控**
   - 使用 Redis INFO 命令监控
   - 配置慢查询日志
   - 监控内存使用率

5. **高可用**
   - 考虑使用 Redis Sentinel（主从+自动故障转移）
   - 或使用 Redis Cluster（分布式集群）

## 故障排除

### 问题 1: 连接失败

```
RuntimeError: RedisClient not initialized. Call initialize() first.
```

**解决方案**: 确保应用启动时调用了 `await get_redis_client()`

### 问题 2: 键不存在

```
HTTPException: 404 - Session not found
```

**解决方案**:
- 检查会话是否已创建
- 检查 TTL 是否过期
- 使用 `redis-cli KEYS "interview:*"` 查看现有键

### 问题 3: 内存不足

```
Redis error: OOM command not allowed when used memory > 'maxmemory'
```

**解决方案**:
- 增加 Redis maxmemory 配置
- 为所有键设置合理的 TTL
- 使用淘汰策略清理旧数据

## 总结

Redis 配置已完成，包括：

- ✅ 依赖安装和配置
- ✅ 完整的 Redis 异步客户端
- ✅ 面试状态管理系统
- ✅ 应用生命周期集成
- ✅ 详细的文档和示例
- ✅ 测试脚本

所有代码都遵循项目现有的编码风格，使用类型提示和文档字符串。

**总代码量**: 754 行（redis_client.py + interview_state.py）
