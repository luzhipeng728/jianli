#!/usr/bin/env python3
"""
更新面试记录中的候选人音频路径和文本
使用阿里云ASR重新识别音频内容
"""

import os
import sys
import json
import asyncio
import wave
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.services.asr_service import ParaformerASRSession


async def transcribe_audio_file(audio_path: str) -> str:
    """使用 Paraformer ASR 识别音频文件

    Args:
        audio_path: WAV 音频文件路径

    Returns:
        识别出的文本
    """
    # 读取 WAV 文件
    with wave.open(audio_path, 'rb') as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        audio_data = wf.readframes(wf.getnframes())

    print(f"  Audio: {sample_rate}Hz, {n_channels}ch, {sample_width*8}bit")

    # 如果是立体声，转换为单声道
    if n_channels == 2:
        import struct
        samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
        mono_samples = [(samples[i] + samples[i+1]) // 2 for i in range(0, len(samples), 2)]
        audio_data = struct.pack(f'<{len(mono_samples)}h', *mono_samples)

    # 收集转录结果
    results = []
    finished_event = asyncio.Event()

    def on_transcript(text: str, is_final: bool):
        if is_final and text.strip():
            results.append(text.strip())
            print(f"  [ASR] Final: {text[:50]}...")

    def on_error(error: str):
        print(f"  [ASR] Error: {error}")

    # 创建 ASR 会话
    session = ParaformerASRSession(
        on_transcript=on_transcript,
        on_error=on_error,
        sample_rate=sample_rate
    )

    try:
        # 连接
        connected = await session.connect()
        if not connected:
            return ""

        # 分块发送音频（每次发送 3200 字节，约 100ms）
        chunk_size = 3200
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            await session.send_audio(chunk)
            await asyncio.sleep(0.05)  # 模拟实时流

        # 发送结束信号
        await session.finish()

        # 等待最后的结果
        await asyncio.sleep(2)

    finally:
        await session.close()

    return "".join(results)

async def update_interview_audio(session_id: str):
    """更新面试记录中的音频路径和文本"""

    # 路径
    interview_dir = Path(f"/data/interviews/{session_id}")
    record_file = interview_dir / "record.json"
    audio_dir = interview_dir / "audio"

    if not record_file.exists():
        print(f"Record not found: {record_file}")
        return False

    # 读取记录
    with open(record_file, 'r', encoding='utf-8') as f:
        record = json.load(f)

    # 获取所有候选人音频文件
    audio_files = sorted(audio_dir.glob("round_*_candidate.wav"))
    print(f"Found {len(audio_files)} candidate audio files")

    # 找到所有候选人对话
    candidate_dialogues = [
        (i, d) for i, d in enumerate(record['dialogues'])
        if d['role'] == 'candidate'
    ]
    print(f"Found {len(candidate_dialogues)} candidate dialogues")

    # 匹配音频文件和对话
    for audio_file in audio_files:
        # 从文件名提取轮次: round_0_candidate.wav -> 0
        filename = audio_file.name
        round_num = int(filename.split('_')[1])

        print(f"\nProcessing {filename} (round {round_num})...")

        # 找到对应的候选人对话（按顺序匹配）
        if round_num < len(candidate_dialogues):
            idx, dialogue = candidate_dialogues[round_num]

            # 更新音频路径
            relative_path = f"audio/{filename}"
            record['dialogues'][idx]['audio_path'] = relative_path

            # 使用ASR重新识别
            try:
                print(f"  Transcribing audio...")
                transcript = await transcribe_audio_file(str(audio_file))
                if transcript:
                    old_text = dialogue['content']
                    record['dialogues'][idx]['content'] = transcript
                    print(f"  Old: {old_text[:50]}...")
                    print(f"  New: {transcript[:50]}...")
                else:
                    print(f"  ASR returned empty, keeping original")
            except Exception as e:
                print(f"  ASR failed: {e}, keeping original")

            print(f"  audio_path: {relative_path}")
        else:
            print(f"  No matching dialogue for round {round_num}")

    # 保存更新后的记录
    with open(record_file, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"\nRecord updated: {record_file}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_interview_audio.py <session_id>")
        sys.exit(1)

    session_id = sys.argv[1]
    asyncio.run(update_interview_audio(session_id))
