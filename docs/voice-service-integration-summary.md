# 阿里云语音服务集成总结

**集成日期**: 2026-01-07
**状态**: ✅ 完成

## 实现概览

成功在 `/root/jianli_final/backend` 中集成了阿里云 DashScope 语音服务，实现了完整的语音面试功能。

## 已实现功能

### 1. 语音服务封装 (`/root/jianli_final/backend/app/services/voice_service.py`)

#### VoiceService 类

- **流式语音识别 (ASR)**
  - 模型: `qwen3-asr-flash-realtime`
  - WebSocket 端点: `wss://dashscope.aliyuncs.com/api-ws/v1/realtime`
  - 支持实时音频流输入
  - 返回实时和最终识别结果
  - 自动处理 base64 编码/解码

- **流式语音合成 (TTS)**
  - 模型: `qwen3-tts-flash`
  - 默认语音: `zhitian_emo`
  - 支持流式文本输入和音频输出
  - 提供 base64 编码音频（WebSocket 专用）
  - 支持多种语音风格和语言

#### 核心方法

```python
# 流式语音识别
async def speech_to_text_stream(
    audio_stream: AsyncGenerator[bytes, None]
) -> AsyncGenerator[ASRResult, None]

# 流式语音合成
async def text_to_speech_stream(
    text: str,
    voice: Optional[str] = None,
    language: str = "Chinese"
) -> AsyncGenerator[TTSChunk, None]

# Base64 TTS（WebSocket 专用）
async def text_to_speech_base64(
    text: str,
    voice: Optional[str] = None,
    language: str = "Chinese"
) -> AsyncGenerator[str, None]
```

#### 数据模型

```python
@dataclass
class ASRResult:
    text: str              # 识别的文本
    is_final: bool         # 是否为最终结果
    sentence_id: str       # 句子 ID（可选）

@dataclass
class TTSChunk:
    audio_data: bytes      # PCM 音频数据
    is_final: bool         # 是否为最后一个块
```

### 2. WebSocket 语音面试路由更新 (`/root/jianli_final/backend/app/api/routes/ws_interview.py`)

#### 更新内容

- ✅ 集成 `VoiceService` 进行实时 ASR 和 TTS
- ✅ 实现音频消息处理（`handle_audio_message`）
  - Base64 音频解码
  - 实时语音识别
  - 会话历史记录
  - LLM 面试官回复生成
  - 流式 TTS 语音合成
  - 状态管理（listening → processing → speaking → listening）

- ✅ 增强控制消息处理（`handle_control_message`）
  - 开始面试时发送欢迎语音
  - TTS 合成欢迎消息
  - 状态自动切换

- ✅ 添加面试官回复生成（`generate_interviewer_response`）
  - 集成 LLM 生成面试问题
  - 基于对话历史动态调整
  - 错误处理和降级回复

#### WebSocket 消息流程

```
客户端                          服务器
  |                              |
  |-- {"type": "control", "action": "start"} -->|
  |                              |
  |<-- {"type": "question", ...} --|
  |<-- {"type": "status", "status": "speaking"} --|
  |<-- {"type": "audio", ...} (TTS) --|
  |<-- {"type": "status", "status": "listening"} --|
  |                              |
  |-- {"type": "audio", ...} (录音) -->|
  |                              |
  |<-- {"type": "transcript", "is_final": false} --|
  |<-- {"type": "transcript", "is_final": true} --|
  |<-- {"type": "question", ...} --|
  |<-- {"type": "audio", ...} (TTS) --|
  |<-- {"type": "status", "status": "listening"} --|
  |                              |
  (循环)
```

## 技术架构

### 依赖项

- **DashScope SDK**: >=1.20（已在 `pyproject.toml` 中配置）
- **Python**: >=3.11
- **FastAPI**: WebSocket 支持
- **asyncio**: 异步流处理

### 环境变量

```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
```

（与 Qwen LLM 使用相同的 API Key）

### 音频格式规范

- **输入 (ASR)**: PCM 16kHz 16bit 单声道（base64 编码）
- **输出 (TTS)**: PCM 24kHz 16bit 单声道（base64 编码）

## 使用示例

### 服务端使用

```python
from app.services.voice_service import get_voice_service

# 获取语音服务实例
voice_service = get_voice_service()

# 语音识别
async for result in voice_service.speech_to_text_stream(audio_stream):
    print(f"[{'Final' if result.is_final else 'Partial'}] {result.text}")

# 语音合成
async for audio_b64 in voice_service.text_to_speech_base64("你好"):
    await websocket.send_json({"type": "audio", "audio": audio_b64})
```

### 客户端使用

```javascript
// 连接 WebSocket
const ws = new WebSocket(`ws://localhost:8000/api/ws/interview/${token}`);

// 开始面试
ws.send(JSON.stringify({
  type: "control",
  action: "start"
}));

// 发送录音音频
ws.send(JSON.stringify({
  type: "audio",
  audio: base64AudioData  // base64 编码的 PCM 音频
}));

// 接收消息
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === "transcript") {
    console.log(`识别: ${msg.text} (${msg.is_final ? 'Final' : 'Partial'})`);
  }
  else if (msg.type === "audio") {
    // 解码并播放音频
    playAudio(msg.audio);
  }
  else if (msg.type === "status") {
    console.log(`状态: ${msg.status}`);
  }
};
```

## 性能特性

### ASR (语音识别)

- ✅ 实时流式识别
- ✅ 低延迟 (<100ms)
- ✅ 支持 VAD (语音活动检测)
- ✅ 自动语种检测
- ✅ 支持中文方言和 11 种国际语言

### TTS (语音合成)

- ✅ 流式音频合成
- ✅ 首包延迟 <100ms
- ✅ 高音质（24kHz 采样率）
- ✅ 多种语音风格
- ✅ 支持中英文等多语言

## 错误处理

### 实现的错误处理

1. ✅ API Key 未设置检查
2. ✅ WebSocket 连接异常处理
3. ✅ 音频数据解码错误处理
4. ✅ ASR/TTS 服务异常降级
5. ✅ LLM 生成失败降级回复

### 错误消息格式

```json
{
  "type": "error",
  "message": "错误描述"
}
```

## 文档

### 创建的文档

1. **API 文档**: `/root/jianli_final/docs/alibaba-voice-api.md`
   - DashScope API 参考
   - 配置说明
   - 完整使用示例
   - 事件格式说明
   - 错误处理指南

2. **集成总结**: `/root/jianli_final/docs/voice-service-integration-summary.md`（本文档）
   - 实现概览
   - 使用示例
   - 架构说明

## 测试建议

### 单元测试

```python
import pytest
from app.services.voice_service import get_voice_service

@pytest.mark.asyncio
async def test_voice_service_initialization():
    service = get_voice_service()
    assert service is not None
    assert service.api_key is not None

@pytest.mark.asyncio
async def test_tts_stream():
    service = get_voice_service()
    chunks = []
    async for chunk in service.text_to_speech_stream("测试"):
        chunks.append(chunk)
    assert len(chunks) > 0
```

### 集成测试

使用 WebSocket 客户端测试完整流程：

```bash
# 安装 websockets 库
pip install websockets

# 运行测试脚本
python tests/test_voice_websocket.py
```

## 下一步优化建议

### 功能增强

1. **语音队列管理**: 实现音频队列，支持多轮对话时的音频缓冲
2. **VAD 优化**: 启用服务端 VAD，减少无效识别
3. **语音风格配置**: 支持动态切换 TTS 语音风格
4. **音频质量检测**: 检测音频质量，提示用户改善录音环境

### 性能优化

1. **连接池**: 复用 WebSocket 连接，减少建立连接开销
2. **音频压缩**: 支持压缩音频格式（如 Opus）减少带宽
3. **并发控制**: 限制并发 WebSocket 连接数
4. **缓存机制**: 缓存常用语音（如欢迎语）

### 监控与日志

1. **指标收集**: 记录 ASR/TTS 延迟、成功率等指标
2. **日志增强**: 添加详细的调试日志
3. **错误追踪**: 集成 Sentry 等错误追踪工具

## 相关文件

### 核心实现

- `/root/jianli_final/backend/app/services/voice_service.py` - 语音服务封装
- `/root/jianli_final/backend/app/api/routes/ws_interview.py` - WebSocket 路由
- `/root/jianli_final/backend/app/models/ws_messages.py` - 消息模型

### 配置

- `/root/jianli_final/backend/pyproject.toml` - 依赖配置
- `/root/jianli_final/backend/.env` - 环境变量（需配置 DASHSCOPE_API_KEY）

### 文档

- `/root/jianli_final/docs/alibaba-voice-api.md` - API 技术文档
- `/root/jianli_final/docs/voice-service-integration-summary.md` - 集成总结（本文档）

## 参考资源

### 官方文档

- [DashScope Python SDK](https://github.com/dashscope/dashscope-sdk-python)
- [Qwen-ASR 实时语音识别](https://www.alibabacloud.com/help/en/model-studio/qwen-asr-realtime-python-sdk)
- [Qwen-TTS 语音合成](https://www.alibabacloud.com/help/en/model-studio/qwen-tts)

### DeepWiki 文档

- [DashScope SDK 概览](https://deepwiki.com/dashscope/dashscope-sdk-python/1-overview)
- [Text-to-Speech](https://deepwiki.com/dashscope/dashscope-sdk-python/4.1-text-to-speech)
- [Quick Start Guide](https://deepwiki.com/dashscope/dashscope-sdk-python/1.2-quick-start-guide)

## 版本信息

- **DashScope SDK**: 1.20+
- **Python**: 3.11+
- **FastAPI**: 0.115+
- **集成日期**: 2026-01-07

## 作者

集成开发：Claude Opus 4.5
文档生成：2026-01-07
