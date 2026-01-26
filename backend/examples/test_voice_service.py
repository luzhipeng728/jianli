"""语音服务测试示例

使用前请确保设置环境变量:
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxx"

运行方式:
cd /root/jianli_final/backend
source .venv/bin/activate
python examples/test_voice_service.py
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.voice_service import get_voice_service


async def test_tts():
    """测试 TTS 语音合成"""
    print("\n=== 测试 TTS 语音合成 ===")

    voice_service = get_voice_service()

    if not voice_service.api_key:
        print("❌ 错误: DASHSCOPE_API_KEY 未设置")
        print("请运行: export DASHSCOPE_API_KEY='your-api-key'")
        return

    try:
        test_text = "你好，欢迎参加本次面试。"
        print(f"合成文本: {test_text}")

        chunk_count = 0
        total_bytes = 0

        async for chunk in voice_service.text_to_speech_stream(
            text=test_text,
            voice="zhitian_emo",
            language="Chinese"
        ):
            if not chunk.is_final:
                chunk_count += 1
                total_bytes += len(chunk.audio_data)
                print(f"  收到音频块 #{chunk_count}: {len(chunk.audio_data)} 字节")

        print(f"\n✅ TTS 测试成功!")
        print(f"   总音频块数: {chunk_count}")
        print(f"   总音频大小: {total_bytes} 字节")

    except Exception as e:
        print(f"❌ TTS 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_tts_base64():
    """测试 Base64 编码的 TTS（WebSocket 专用）"""
    print("\n=== 测试 Base64 TTS ===")

    voice_service = get_voice_service()

    if not voice_service.api_key:
        print("❌ 错误: DASHSCOPE_API_KEY 未设置")
        return

    try:
        test_text = "测试 Base64 编码的语音合成。"
        print(f"合成文本: {test_text}")

        chunk_count = 0

        async for audio_b64 in voice_service.text_to_speech_base64(
            text=test_text,
            voice="zhitian_emo"
        ):
            chunk_count += 1
            print(f"  收到 Base64 音频块 #{chunk_count}: {len(audio_b64)} 字符")

        print(f"\n✅ Base64 TTS 测试成功!")
        print(f"   总音频块数: {chunk_count}")

    except Exception as e:
        print(f"❌ Base64 TTS 测试失败: {e}")


async def test_asr():
    """测试 ASR 语音识别

    注意: 此测试需要真实的音频数据
    这里仅演示 API 调用方式
    """
    print("\n=== ASR 语音识别测试 ===")
    print("⚠️  需要真实音频数据，此处仅演示 API 用法")

    voice_service = get_voice_service()

    if not voice_service.api_key:
        print("❌ 错误: DASHSCOPE_API_KEY 未设置")
        return

    # 演示代码（需要真实音频文件）
    print("""
示例代码:

async def audio_generator():
    # 从文件或麦克风读取音频
    with open('audio.pcm', 'rb') as f:
        while True:
            chunk = f.read(3200)  # 100ms @ 16kHz
            if not chunk:
                break
            yield chunk

async for result in voice_service.speech_to_text_stream(audio_generator()):
    print(f"[{'Final' if result.is_final else 'Partial'}] {result.text}")
    """)


async def main():
    """主函数"""
    print("=" * 60)
    print("阿里云语音服务测试")
    print("=" * 60)

    # 检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print(f"✅ API Key 已配置: {api_key[:10]}...")
    else:
        print("⚠️  API Key 未配置")
        print("   请运行: export DASHSCOPE_API_KEY='your-api-key'")

    # 运行测试
    await test_tts()
    await test_tts_base64()
    await test_asr()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
