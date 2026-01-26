#!/usr/bin/env python3
"""
快速测试面试结束流程
通过HR干预WebSocket强制结束面试并验证评估是否正确生成
"""

import asyncio
import websockets
import json
import sys

async def test_force_end(session_id: str):
    """通过HR干预强制结束面试"""
    hr_ws_url = f"ws://localhost:8002/ws/hr-monitor/{session_id}"

    print(f"[Test] Connecting to HR monitor: {hr_ws_url}")

    try:
        async with websockets.connect(hr_ws_url) as ws:
            # 订阅会话
            await ws.send(json.dumps({"type": "subscribe"}))
            print("[Test] Subscribed to session")

            # 等待订阅确认
            await asyncio.sleep(0.5)

            # 发送强制结束命令
            print("[Test] Sending force_end command...")
            await ws.send(json.dumps({
                "type": "intervention",
                "command": "force_end",
                "data": {"reason": "testing"}
            }))

            # 等待响应
            print("[Test] Waiting for interview_end response...")
            timeout = 30  # 30秒超时
            start = asyncio.get_event_loop().time()

            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(response)
                    print(f"[Test] Received: {data.get('type')}")

                    if data.get("type") == "interview_complete":
                        print("[Test] ✓ Interview completed successfully!")
                        if data.get("evaluation"):
                            eval_data = data["evaluation"]
                            print(f"[Test] Score: {eval_data.get('overall_score')}")
                            print(f"[Test] Recommendation: {eval_data.get('recommendation')}")
                        return True

                    if data.get("type") == "error":
                        print(f"[Test] ✗ Error: {data.get('message')}")
                        return False

                except asyncio.TimeoutError:
                    if asyncio.get_event_loop().time() - start > timeout:
                        print("[Test] ✗ Timeout waiting for response")
                        return False
                    continue

    except Exception as e:
        print(f"[Test] ✗ Connection error: {e}")
        return False

async def test_candidate_interview(session_id: str, auto_responses: int = 3):
    """模拟候选人进行面试，自动回答指定轮数后检查是否能正常结束"""
    candidate_ws_url = f"ws://localhost:8002/ws/structured-interview/{session_id}"

    print(f"[Test] Connecting as candidate: {candidate_ws_url}")

    try:
        async with websockets.connect(candidate_ws_url) as ws:
            # 发送初始化消息
            await ws.send(json.dumps({
                "type": "init",
                "session_id": session_id,
                "resume_id": "test",
                "jd_id": "test",
                "resume_summary": "测试候选人",
                "job_info": "测试岗位",
                "position_name": "测试工程师"
            }))

            responses_sent = 0
            interview_ended = False

            while not interview_ended and responses_sent < auto_responses:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(response)
                    msg_type = data.get("type")

                    if msg_type == "response_end":
                        # 面试官说完了，模拟候选人回答
                        responses_sent += 1
                        print(f"[Test] Sending auto response {responses_sent}/{auto_responses}")

                        # 模拟发送音频（空白音频，只是触发流程）
                        await ws.send(json.dumps({
                            "type": "text",  # 使用文本模式测试
                            "text": f"这是我的第{responses_sent}个回答，我有丰富的相关经验。"
                        }))

                    elif msg_type == "interview_end":
                        print("[Test] ✓ Interview ended normally!")
                        interview_ended = True
                        if data.get("evaluation"):
                            print(f"[Test] Score: {data['evaluation'].get('overall_score')}")
                        return True

                    elif msg_type == "phase_change":
                        print(f"[Test] Phase changed to: {data.get('phase')}")

                except asyncio.TimeoutError:
                    print("[Test] Timeout waiting for response")
                    break

            if not interview_ended:
                print(f"[Test] Sent {responses_sent} responses, interview not ended yet")
                return False

    except Exception as e:
        print(f"[Test] Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_interview_end.py <session_id> [force_end|simulate]")
        print("  force_end - 通过HR干预强制结束面试")
        print("  simulate  - 模拟候选人自动回答")
        sys.exit(1)

    session_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "force_end"

    if mode == "force_end":
        result = asyncio.run(test_force_end(session_id))
    else:
        result = asyncio.run(test_candidate_interview(session_id))

    sys.exit(0 if result else 1)
