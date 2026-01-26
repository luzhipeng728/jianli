import asyncio
import json
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool
from app.config import get_settings


class RedisClient:
    """单例模式的 Redis 异步客户端"""

    _instance: Optional["RedisClient"] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """初始化 Redis 连接池"""
        if self._pool is None:
            settings = get_settings()
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=50,
                decode_responses=True,
                encoding="utf-8",
            )
            self._client = Redis(connection_pool=self._pool)

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._client = None
        self._pool = None

    @property
    def client(self) -> Redis:
        """获取 Redis 客户端实例"""
        if self._client is None:
            raise RuntimeError("RedisClient not initialized. Call initialize() first.")
        return self._client

    # ==================== 基础操作 ====================

    async def get(self, key: str) -> Optional[str]:
        """获取字符串值"""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """设置字符串值

        Args:
            key: 键
            value: 值
            ex: 过期时间（秒）
            px: 过期时间（毫秒）
            nx: 只在键不存在时设置
            xx: 只在键存在时设置
        """
        return await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)

    async def delete(self, *keys: str) -> int:
        """删除一个或多个键"""
        return await self.client.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """检查键是否存在"""
        return await self.client.exists(*keys)

    async def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间（秒）"""
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间（秒）"""
        return await self.client.ttl(key)

    # ==================== JSON 操作 ====================

    async def get_json(self, key: str) -> Optional[Any]:
        """获取并解析 JSON 值"""
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    async def set_json(
        self, key: str, value: Any, ex: Optional[int] = None
    ) -> bool:
        """设置 JSON 值"""
        json_str = json.dumps(value, ensure_ascii=False)
        return await self.set(key, json_str, ex=ex)

    # ==================== 列表操作 ====================

    async def lpush(self, key: str, *values: str) -> int:
        """从列表左侧推入一个或多个值"""
        return await self.client.lpush(key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        """从列表右侧推入一个或多个值"""
        return await self.client.rpush(key, *values)

    async def lpop(self, key: str, count: Optional[int] = None) -> Optional[str]:
        """从列表左侧弹出值"""
        return await self.client.lpop(key, count)

    async def rpop(self, key: str, count: Optional[int] = None) -> Optional[str]:
        """从列表右侧弹出值"""
        return await self.client.rpop(key, count)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        """获取列表指定范围的元素"""
        return await self.client.lrange(key, start, end)

    async def llen(self, key: str) -> int:
        """获取列表长度"""
        return await self.client.llen(key)

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """修剪列表，只保留指定范围的元素"""
        return await self.client.ltrim(key, start, end)

    # ==================== 哈希操作 ====================

    async def hget(self, key: str, field: str) -> Optional[str]:
        """获取哈希表中指定字段的值"""
        return await self.client.hget(key, field)

    async def hset(self, key: str, field: str, value: str) -> int:
        """设置哈希表中指定字段的值"""
        return await self.client.hset(key, field, value)

    async def hgetall(self, key: str) -> dict:
        """获取哈希表中所有字段和值"""
        return await self.client.hgetall(key)

    async def hmset(self, key: str, mapping: dict) -> bool:
        """设置哈希表中多个字段的值"""
        return await self.client.hset(key, mapping=mapping)

    async def hdel(self, key: str, *fields: str) -> int:
        """删除哈希表中一个或多个字段"""
        return await self.client.hdel(key, *fields)

    async def hexists(self, key: str, field: str) -> bool:
        """检查哈希表中是否存在指定字段"""
        return await self.client.hexists(key, field)

    # ==================== 集合操作 ====================

    async def sadd(self, key: str, *members: str) -> int:
        """向集合添加一个或多个成员"""
        return await self.client.sadd(key, *members)

    async def srem(self, key: str, *members: str) -> int:
        """从集合中移除一个或多个成员"""
        return await self.client.srem(key, *members)

    async def smembers(self, key: str) -> set:
        """获取集合中的所有成员"""
        return await self.client.smembers(key)

    async def sismember(self, key: str, member: str) -> bool:
        """检查成员是否在集合中"""
        return await self.client.sismember(key, member)

    # ==================== 有序集合操作 ====================

    async def zadd(self, key: str, mapping: dict) -> int:
        """向有序集合添加成员"""
        return await self.client.zadd(key, mapping)

    async def zrange(
        self, key: str, start: int, end: int, withscores: bool = False
    ) -> list:
        """获取有序集合指定范围的成员"""
        return await self.client.zrange(key, start, end, withscores=withscores)

    async def zrem(self, key: str, *members: str) -> int:
        """从有序集合中移除成员"""
        return await self.client.zrem(key, *members)

    # ==================== 发布订阅 ====================

    async def publish(self, channel: str, message: str) -> int:
        """发布消息到指定频道"""
        return await self.client.publish(channel, message)

    async def subscribe(self, *channels: str):
        """订阅一个或多个频道"""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub

    # ==================== 面试状态专用方法 ====================

    async def set_interview_context(
        self, session_id: str, context: dict, ttl: int = 3600
    ) -> bool:
        """设置面试会话上下文

        Args:
            session_id: 会话ID
            context: 上下文数据
            ttl: 过期时间（秒），默认1小时
        """
        key = f"interview:context:{session_id}"
        return await self.set_json(key, context, ex=ttl)

    async def get_interview_context(self, session_id: str) -> Optional[dict]:
        """获取面试会话上下文"""
        key = f"interview:context:{session_id}"
        return await self.get_json(key)

    async def delete_interview_context(self, session_id: str) -> int:
        """删除面试会话上下文"""
        key = f"interview:context:{session_id}"
        return await self.delete(key)

    async def push_control_command(
        self, session_id: str, command: dict
    ) -> int:
        """推送控场指令到队列

        Args:
            session_id: 会话ID
            command: 控场指令（字典）
        """
        key = f"interview:commands:{session_id}"
        command_str = json.dumps(command, ensure_ascii=False)
        # 推入队列尾部
        count = await self.rpush(key, command_str)
        # 设置过期时间（1小时）
        await self.expire(key, 3600)
        return count

    async def pop_control_command(self, session_id: str) -> Optional[dict]:
        """从队列头部弹出控场指令

        Args:
            session_id: 会话ID
        """
        key = f"interview:commands:{session_id}"
        command_str = await self.lpop(key)
        if command_str is None:
            return None
        try:
            return json.loads(command_str)
        except json.JSONDecodeError:
            return None

    async def get_command_queue_length(self, session_id: str) -> int:
        """获取控场指令队列长度"""
        key = f"interview:commands:{session_id}"
        return await self.llen(key)

    async def clear_command_queue(self, session_id: str) -> int:
        """清空控场指令队列"""
        key = f"interview:commands:{session_id}"
        return await self.delete(key)

    async def set_agent_state(
        self, session_id: str, agent_id: str, state: dict, ttl: int = 3600
    ) -> bool:
        """设置 Agent 状态

        Args:
            session_id: 会话ID
            agent_id: Agent ID
            state: 状态数据
            ttl: 过期时间（秒）
        """
        key = f"interview:agent:{session_id}:{agent_id}"
        return await self.set_json(key, state, ex=ttl)

    async def get_agent_state(
        self, session_id: str, agent_id: str
    ) -> Optional[dict]:
        """获取 Agent 状态"""
        key = f"interview:agent:{session_id}:{agent_id}"
        return await self.get_json(key)

    async def delete_agent_state(
        self, session_id: str, agent_id: str
    ) -> int:
        """删除 Agent 状态"""
        key = f"interview:agent:{session_id}:{agent_id}"
        return await self.delete(key)


# 全局单例实例
_redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """获取 Redis 客户端实例（依赖注入用）"""
    if _redis_client._client is None:
        await _redis_client.initialize()
    return _redis_client
