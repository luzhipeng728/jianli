# 阿里云语音服务集成指南

本文档提供阿里云 DashScope 语音服务在简历面试系统中的集成和使用说明。

## 目录

- [功能概述](#功能概述)
- [环境配置](#环境配置)
- [快速开始](#快速开始)
- [API 使用](#api-使用)
- [WebSocket 集成](#websocket-集成)
- [测试](#测试)
- [故障排查](#故障排查)

## 功能概述

### 已实现功能

✅ **流式语音识别 (ASR)**
- 实时音频流转文字
- 支持中文、英文等 11 种语言
- 低延迟 (<100ms)
- 自动 VAD (语音活动检测)

✅ **流式语音合成 (TTS)**
- 文字转自然语音
- 多种语音风格可选
- 首包延迟 <100ms
- 支持流式输入输出

✅ **WebSocket 语音面试**
- 完整的双向语音交互
- 实时转录和合成
- 集成 LLM 面试官
- 状态管理和错误处理

## 环境配置

### 1. 安装依赖

依赖已在 `pyproject.toml` 中配置：

```toml
[project]
dependencies = [
    "dashscope>=1.20",
    # ... 其他依赖
]
```

安装方式：

```bash
cd /root/jianli_final/backend
pip install -e .
```

### 2. 配置 API Key

#### 方式 1: 环境变量（推荐）

```bash
# Linux/macOS
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxx"

# 永久配置
echo 'export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

#### 方式 2: .env 文件

```bash
cd /root/jianli_final/backend
echo 'DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx' >> .env
```

#### 获取 API Key

1. 访问 [DashScope 控制台](https://dashscope.aliyun.com/)
2. 开通服务并创建 API Key
3. 复制 API Key（格式: `sk-xxxxxxxxxxxxx`）

### 3. 验证配置

```bash
python3 -c "import os; print('API Key:', os.getenv('DASHSCOPE_API_KEY')[:10] + '...')"
```

## 快速开始

### 1. 导入语音服务

```python
from app.services.voice_service import get_voice_service

# 获取服务实例（单例模式）
voice_service = get_voice_service()
```

### 2. 语音合成 (TTS)

```python
async def synthesize_speech():
    """文字转语音示例"""
    async for chunk in voice_service.text_to_speech_stream(
        text="你好，欢迎参加面试",
        voice="zhitian_emo",
        language="Chinese"
    ):
        # 处理音频数据
        if not chunk.is_final:
            audio_data = chunk.audio_data  # bytes
            # 播放或保存音频...
```

### 3. 语音识别 (ASR)

```python
async def recognize_speech(audio_stream):
    """语音转文字示例"""
    async for result in voice_service.speech_to_text_stream(audio_stream):
        if result.is_final:
            print(f"最终识别: {result.text}")
        else:
            print(f"实时识别: {result.text}")
```

### 4. 运行测试

```bash
cd /root/jianli_final/backend
source .venv/bin/activate
python examples/test_voice_service.py
```

## API 使用

### VoiceService 类

位置: `/root/jianli_final/backend/app/services/voice_service.py`

#### 初始化

```python
from app.services.voice_service import VoiceService

# 自动从环境变量读取 API Key
service = VoiceService()
```

#### 方法说明

##### 1. speech_to_text_stream

流式语音识别。

**签名:**
```python
async def speech_to_text_stream(
    self,
    audio_stream: AsyncGenerator[bytes, None]
) -> AsyncGenerator[ASRResult, None]
```

**参数:**
- `audio_stream`: 音频流生成器
  - 格式: PCM 16kHz 16bit 单声道
  - 类型: `AsyncGenerator[bytes, None]`

**返回:**
- `AsyncGenerator[ASRResult, None]`
  - `text`: 识别的文本
  - `is_final`: 是否为最终结果
  - `sentence_id`: 句子 ID（可选）

**示例:**
```python
async def audio_generator():
    with open("audio.pcm", "rb") as f:
        while True:
            chunk = f.read(3200)  # 100ms @ 16kHz
            if not chunk:
                break
            yield chunk

async for result in service.speech_to_text_stream(audio_generator()):
    print(f"[{'Final' if result.is_final else 'Partial'}] {result.text}")
```

##### 2. text_to_speech_stream

流式语音合成（返回 PCM 音频）。

**签名:**
```python
async def text_to_speech_stream(
    self,
    text: str,
    voice: Optional[str] = None,
    language: str = "Chinese"
) -> AsyncGenerator[TTSChunk, None]
```

**参数:**
- `text`: 要合成的文本
- `voice`: 语音类型
  - 默认: `zhitian_emo`
  - 可选: `Dylan`, `Cherry`, `zhichu_emo`, `zhida_emo`, `zhixiaobai`, `zhixiaoxia`
- `language`: 语言
  - 可选: `Chinese`, `English`, `Auto`

**返回:**
- `AsyncGenerator[TTSChunk, None]`
  - `audio_data`: PCM 音频数据 (bytes)
  - `is_final`: 是否为最后一块

**示例:**
```python
async for chunk in service.text_to_speech_stream(
    text="你好，世界",
    voice="zhitian_emo"
):
    if not chunk.is_final:
        # 播放音频
        play_audio(chunk.audio_data)
```

##### 3. text_to_speech_base64

流式语音合成（返回 base64 编码，WebSocket 专用）。

**签名:**
```python
async def text_to_speech_base64(
    self,
    text: str,
    voice: Optional[str] = None,
    language: str = "Chinese"
) -> AsyncGenerator[str, None]
```

**参数:**
同 `text_to_speech_stream`

**返回:**
- `AsyncGenerator[str, None]` - base64 编码的音频数据

**示例:**
```python
async for audio_b64 in service.text_to_speech_base64("你好"):
    await websocket.send_json({
        "type": "audio",
        "audio": audio_b64
    })
```

## WebSocket 集成

### WebSocket 端点

```
ws://localhost:8000/api/ws/interview/{token}
```

### 客户端消息

#### 开始面试

```json
{
  "type": "control",
  "action": "start"
}
```

#### 发送音频

```json
{
  "type": "audio",
  "audio": "base64_encoded_pcm_audio"
}
```

音频格式要求:
- 编码: base64
- 格式: PCM 16kHz 16bit 单声道

#### 停止面试

```json
{
  "type": "control",
  "action": "stop"
}
```

### 服务器消息

#### 转录结果

```json
{
  "type": "transcript",
  "text": "识别的文本",
  "is_final": false
}
```

#### 语音音频

```json
{
  "type": "audio",
  "audio": "base64_encoded_pcm_audio"
}
```

#### 状态更新

```json
{
  "type": "status",
  "status": "listening"
}
```

可能的状态:
- `listening` - 等待用户说话
- `processing` - 处理中
- `speaking` - 播放语音
- `stopped` - 已停止

#### 面试问题

```json
{
  "type": "question",
  "text": "面试官的问题"
}
```

#### 错误消息

```json
{
  "type": "error",
  "message": "错误描述"
}
```

### 完整交互流程

```
1. 客户端连接 WebSocket
   ↓
2. 客户端发送: {"type": "control", "action": "start"}
   ↓
3. 服务器返回欢迎消息（文本 + 语音）
   ↓
4. 服务器切换到 "listening" 状态
   ↓
5. 客户端录音并发送音频
   ↓
6. 服务器 ASR 识别，返回转录结果
   ↓
7. 服务器调用 LLM 生成回复
   ↓
8. 服务器 TTS 合成语音并发送
   ↓
9. 回到步骤 4（循环）
```

## 测试

### 单元测试

创建测试文件 `tests/test_voice_service.py`:

```python
import pytest
from app.services.voice_service import get_voice_service

@pytest.mark.asyncio
async def test_voice_service_init():
    """测试服务初始化"""
    service = get_voice_service()
    assert service is not None

@pytest.mark.asyncio
async def test_tts_with_api_key():
    """测试 TTS（需要 API Key）"""
    service = get_voice_service()

    if not service.api_key:
        pytest.skip("API Key not configured")

    chunks = []
    async for chunk in service.text_to_speech_stream("测试"):
        chunks.append(chunk)

    assert len(chunks) > 0
```

运行测试:

```bash
cd /root/jianli_final/backend
pytest tests/test_voice_service.py -v
```

### 集成测试

使用示例脚本:

```bash
cd /root/jianli_final/backend
source .venv/bin/activate
python examples/test_voice_service.py
```

### WebSocket 测试

使用 WebSocket 客户端工具或编写测试脚本:

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/api/ws/interview/{token}"

    async with websockets.connect(uri) as ws:
        # 开始面试
        await ws.send(json.dumps({
            "type": "control",
            "action": "start"
        }))

        # 接收消息
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"收到: {data['type']}")

            if data['type'] == 'audio':
                print(f"  音频长度: {len(data['audio'])}")

asyncio.run(test_websocket())
```

## 故障排查

### 问题 1: API Key 未配置

**错误信息:**
```
ValueError: DASHSCOPE_API_KEY not configured
```

**解决方案:**
```bash
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxx"
```

### 问题 2: DashScope SDK 未安装

**错误信息:**
```
ModuleNotFoundError: No module named 'dashscope'
```

**解决方案:**
```bash
cd /root/jianli_final/backend
pip install -e .
```

### 问题 3: WebSocket 连接失败

**可能原因:**
1. 后端服务未启动
2. Token 无效
3. 网络问题

**解决方案:**
```bash
# 启动后端服务
cd /root/jianli_final/backend
uvicorn app.main:app --reload --port 8000

# 检查服务状态
curl http://localhost:8000/health
```

### 问题 4: 音频识别无结果

**可能原因:**
1. 音频格式不正确
2. 音频质量差
3. 音频时长过短

**解决方案:**
- 确保音频为 PCM 16kHz 16bit 单声道
- 音频时长 >1 秒
- 检查 base64 编码是否正确

### 问题 5: TTS 无声音

**可能原因:**
1. 音频数据未正确解码
2. 播放器不支持 PCM 格式
3. 采样率不匹配

**解决方案:**
- 使用支持 PCM 的播放器
- 确认采样率为 24kHz
- 检查音频数据是否完整

## 配置参数

### ASR 配置

在 `voice_service.py` 中可调整:

```python
self.asr_model = "qwen3-asr-flash-realtime"
self.asr_endpoint = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
```

### TTS 配置

```python
self.tts_model = "qwen3-tts-flash"
self.tts_voice = "zhitian_emo"
self.tts_sample_rate = 24000
```

### 可用 TTS 语音

| 语音名称 | 描述 | 适用场景 |
|---------|------|---------|
| `zhitian_emo` | 知甜（情感） | 面试官、客服 |
| `zhichu_emo` | 知楚（情感） | 播音、讲解 |
| `Dylan` | 英文男声 | 英语面试 |
| `Cherry` | 英文女声 | 英语场景 |
| `zhixiaobai` | 知小白 | 通用场景 |

## 性能优化

### 建议

1. **复用服务实例** - 使用单例模式 `get_voice_service()`
2. **控制音频块大小** - ASR 推荐 50-100ms
3. **启用 VAD** - 减少无效识别
4. **限制文本长度** - TTS 建议 <200 字
5. **使用流式合成** - 减少首字延迟

### 监控指标

建议监控:
- ASR 识别延迟
- TTS 合成延迟
- WebSocket 连接数
- 错误率

## 相关文档

- **API 技术文档**: `/root/jianli_final/docs/alibaba-voice-api.md`
- **集成总结**: `/root/jianli_final/docs/voice-service-integration-summary.md`
- **服务实现**: `/root/jianli_final/backend/app/services/voice_service.py`
- **WebSocket 路由**: `/root/jianli_final/backend/app/api/routes/ws_interview.py`

## 参考资源

- [DashScope SDK GitHub](https://github.com/dashscope/dashscope-sdk-python)
- [Qwen-ASR 文档](https://www.alibabacloud.com/help/en/model-studio/qwen-asr-realtime-python-sdk)
- [Qwen-TTS 文档](https://www.alibabacloud.com/help/en/model-studio/qwen-tts)
- [DashScope 控制台](https://dashscope.aliyun.com/)

## 许可证

本项目使用的阿里云 DashScope API 需遵守阿里云服务协议。

---

**最后更新**: 2026-01-07
**版本**: 1.0.0
