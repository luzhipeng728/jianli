"""Redis 连接测试脚本"""

import asyncio
from app.services.redis_client import get_redis_client
from app.services.interview_state import (
    get_interview_state_manager,
    InterviewPhase,
    AgentState,
    ControlCommand,
    CommandType,
)


async def test_redis_basic():
    """测试 Redis 基础操作"""
    print("=== 测试 Redis 基础操作 ===")

    redis = await get_redis_client()

    # 测试字符串操作
    await redis.set("test_key", "test_value", ex=60)
    value = await redis.get("test_key")
    print(f"✓ 字符串操作: {value}")

    # 测试 JSON 操作
    test_data = {"name": "张三", "age": 25, "skills": ["Python", "FastAPI"]}
    await redis.set_json("test_json", test_data, ex=60)
    json_data = await redis.get_json("test_json")
    print(f"✓ JSON 操作: {json_data}")

    # 测试列表操作
    await redis.rpush("test_list", "item1", "item2", "item3")
    items = await redis.lrange("test_list", 0, -1)
    print(f"✓ 列表操作: {items}")

    # 清理
    await redis.delete("test_key", "test_json", "test_list")
    print("✓ 基础操作测试通过\n")


async def test_interview_state():
    """测试面试状态管理"""
    print("=== 测试面试状态管理 ===")

    manager = get_interview_state_manager()
    session_id = "test_session_001"

    # 创建会话
    context = await manager.create_session(
        session_id=session_id,
        candidate_id="candidate_001",
        resume_id="resume_001",
        job_position="Python后端工程师",
        config={"duration": 60, "difficulty": "medium"},
        ttl=300  # 5分钟
    )
    print(f"✓ 创建会话: {context.session_id}")

    # 获取会话
    retrieved = await manager.get_session(session_id)
    print(f"✓ 获取会话: {retrieved.job_position}")

    # 切换阶段
    await manager.change_phase(session_id, InterviewPhase.TECHNICAL)
    updated = await manager.get_session(session_id)
    print(f"✓ 切换阶段: {updated.current_phase}")

    # 添加对话
    await manager.add_conversation(
        session_id,
        role="interviewer",
        content="请介绍一下你的项目经验",
        metadata={"phase": "technical"}
    )
    await manager.add_conversation(
        session_id,
        role="candidate",
        content="我做过一个基于FastAPI的后端项目...",
        metadata={"phase": "technical"}
    )
    context = await manager.get_session(session_id)
    print(f"✓ 对话记录: {len(context.conversation_history)} 条")

    # 添加评估笔记
    await manager.add_evaluation_note(
        session_id,
        category="技术能力",
        score=8.5,
        note="对FastAPI有深入理解"
    )
    context = await manager.get_session(session_id)
    print(f"✓ 评估笔记: {len(context.evaluation_notes)} 条")

    # 清理
    await manager.delete_session(session_id)
    print("✓ 面试状态管理测试通过\n")


async def test_agent_state():
    """测试 Agent 状态管理"""
    print("=== 测试 Agent 状态管理 ===")

    manager = get_interview_state_manager()
    session_id = "test_session_002"

    # 创建 Agent 状态
    agent_state = AgentState(
        agent_id="interviewer_001",
        agent_type="interviewer",
        status="thinking",
        current_task="准备技术问题",
        memory={"last_topic": "FastAPI", "question_count": 3}
    )

    await manager.set_agent_state(session_id, agent_state, ttl=300)
    print(f"✓ 创建 Agent 状态: {agent_state.agent_id}")

    # 获取 Agent 状态
    retrieved = await manager.get_agent_state(session_id, "interviewer_001")
    print(f"✓ 获取 Agent 状态: {retrieved.status}")

    # 更新 Agent 状态
    await manager.update_agent_status(
        session_id,
        "interviewer_001",
        status="speaking",
        current_task="提问技术问题"
    )
    updated = await manager.get_agent_state(session_id, "interviewer_001")
    print(f"✓ 更新 Agent 状态: {updated.status}")

    # 清理
    await manager.delete_agent_state(session_id, "interviewer_001")
    print("✓ Agent 状态管理测试通过\n")


async def test_control_commands():
    """测试控场指令队列"""
    print("=== 测试控场指令队列 ===")

    manager = get_interview_state_manager()
    session_id = "test_session_003"

    # 推送阶段切换指令
    await manager.push_phase_change_command(
        session_id,
        InterviewPhase.TECHNICAL,
        reason="准备阶段完成"
    )
    print("✓ 推送阶段切换指令")

    # 推送提示指令
    await manager.push_hint_command(
        session_id,
        hint_text="注意控制时间",
        target_agent="interviewer_001"
    )
    print("✓ 推送提示指令")

    # 推送中断指令
    await manager.push_interrupt_command(
        session_id,
        reason="候选人需要暂停",
        action="pause"
    )
    print("✓ 推送中断指令")

    # 获取队列长度
    count = await manager.get_command_count(session_id)
    print(f"✓ 指令队列长度: {count}")

    # 弹出指令（按FIFO顺序）
    commands = []
    while True:
        cmd = await manager.pop_command(session_id)
        if cmd is None:
            break
        commands.append(cmd)
        print(f"  - 弹出指令: {cmd.command_type}, 优先级: {cmd.priority}")

    print(f"✓ 共弹出 {len(commands)} 条指令")

    # 清理
    await manager.clear_commands(session_id)
    print("✓ 控场指令队列测试通过\n")


async def main():
    """主测试函数"""
    try:
        await test_redis_basic()
        await test_interview_state()
        await test_agent_state()
        await test_control_commands()

        print("=" * 50)
        print("所有测试通过！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭 Redis 连接
        redis = await get_redis_client()
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
