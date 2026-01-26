# 阿里云 DashScope 流式语音服务 API 技术文档

> 本文档整理阿里云 DashScope 平台的实时语音识别（ASR）和流式语音合成（TTS）服务的技术细节。
>
> 文档生成时间：2026-01-07

---

## 目录

- [概述](#概述)
- [API Key 认证配置](#api-key-认证配置)
- [语音识别 (ASR) 服务](#语音识别-asr-服务)
- [语音合成 (TTS) 服务](#语音合成-tts-服务)
- [附录：参考资源](#附录参考资源)

---

## 概述

阿里云 DashScope 提供基于通义千问的语音服务，与 qwen3-32b 使用相同的 API Key 认证体系。主要特点：

- **统一认证**：使用同一个 DashScope API Key 访问语音和文本模型服务
- **WebSocket 协议**：支持实时双向通信，低延迟
- **流式处理**：支持实时音频输入和流式音频输出
- **Python SDK**：提供高度封装的 SDK，简化开发流程
- **多模型支持**：提供稳定版和快照版模型

---

## API Key 认证配置

### 1. 获取 API Key

1. 访问 [DashScope 控制台](https://dashscope.aliyun.com/)
2. 点击「去开通」→ 阅读协议 → 「立即开通」
3. 打开「API-KEY 管理」页面
4. 点击「创建新的 API-KEY」→ 立即复制保存
5. 注意：最多可创建 3 个同时生效的 API Key，删除后不可恢复

### 2. 配置环境变量

#### Linux/macOS 系统

```bash
# 临时设置（仅当前终端会话有效）
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"

# 永久设置（添加到配置文件）
echo 'export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc

# 或者使用 zsh
echo 'export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows 系统

1. 按 `Win + Q`，搜索"编辑系统环境变量"
2. 点击"环境变量"按钮
3. 在"系统变量"区域点击"新建"
4. 变量名：`DASHSCOPE_API_KEY`
5. 变量值：您的 API Key（如 `sk-xxxxxxxxxxxxxxxx`）

#### Python 代码中使用

```python
import os
import dashscope

# 方式 1：从环境变量读取（推荐）
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 方式 2：直接设置（不推荐，存在泄露风险）
# dashscope.api_key = "sk-xxxxxxxxxxxxxxxx"
```

#### 验证配置

```python
import os

api_key = os.getenv("DASHSCOPE_API_KEY")
if api_key:
    print(f"API Key 已配置: {api_key[:10]}...")
else:
    print("错误：未找到 DASHSCOPE_API_KEY 环境变量")
```

### 3. HTTP 认证方式

在 HTTP/WebSocket 请求头中使用 Bearer 认证：

```
Authorization: Bearer $DASHSCOPE_API_KEY
```

完整请求头示例：

```json
{
  "Authorization": "bearer sk-xxxxxxxxxxxxxxxx",
  "user-agent": "your_platform_info",
  "X-DashScope-WorkSpace": "workspace",
  "X-DashScope-DataInspection": "enable"
}
```

### 4. 注意事项

- **区域差异**：北京和新加坡地域使用不同的 API Key 和 URL
- **安全性**：不要将 API Key 硬编码在代码中或提交到 Git 仓库
- **IDE 重启**：修改环境变量后需要重启 IDE 或终端才能生效
- **密钥轮换**：定期更换 API Key，提高安全性

---

## 语音识别 (ASR) 服务

### 1. 服务概述

阿里云 DashScope 提供多个实时语音识别服务：

| 服务名称 | 模型代码 | 适用场景 |
|---------|---------|---------|
| **Qwen3-ASR-Flash-Realtime** | `qwen3-asr-flash-realtime` | 通用实时语音识别（推荐） |
| **Fun-ASR-Realtime** | `fun-asr-realtime` | 高精度实时语音识别 |
| **Paraformer-Realtime** | `paraformer-realtime` | 传统实时语音识别 |

本文档重点介绍 **Qwen3-ASR-Flash-Realtime**，这是最新的通义千问实时语音识别服务。

### 2. WebSocket 接口

#### 接口地址

- **北京地域**：`wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=<model_name>`
- **新加坡地域**：`wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime?model=<model_name>`

示例：
```
wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-asr-flash-realtime
```

#### 认证方式

在 WebSocket 连接的请求头中传递：

```json
{
  "Authorization": "bearer sk-xxxxxxxxxxxxxxxx"
}
```

### 3. 模型版本

| 版本类型 | 模型名称 | 说明 |
|---------|---------|------|
| 稳定版 | `qwen3-asr-flash-realtime` | 自动指向最新稳定版本 |
| 快照版 | `qwen3-asr-flash-realtime-2025-10-27` | 特定日期版本 |

### 4. 音频参数

#### 支持的音频格式

- **格式**：wav、mp3、flac、aac、amr、ogg、opus 等 16 种格式
- **推荐格式**：PCM (wav)

#### 音频规格

- **采样率**：16kHz（推荐）、支持 16kHz-48kHz
- **声道**：单声道（Mono）
- **位深度**：16-bit
- **比特率**：128kbps 以上（推荐）
- **音频长度**：不超过 3 分钟
- **文件大小**：不超过 10MB

#### FFmpeg 音频转换示例

```bash
# 转换为 16kHz 单声道 PCM 格式
ffmpeg -i input.mp3 \
  -ar 16000 \
  -ac 1 \
  -sample_fmt s16 \
  output.wav
```

### 5. 交互模式

#### VAD 模式（语音活动检测）

服务器自动检测语音的开始和结束：

- `input_audio_buffer.speech_started` - 检测到语音开始
- `input_audio_buffer.speech_stopped` - 检测到语音结束
- 适用于对话、会议等自然语音场景

#### Manual 模式（手动控制）

客户端手动控制识别的开始和结束：

- 通过客户端指令控制识别边界
- 适用于命令词识别、固定长度语音等场景

### 6. WebSocket 事件格式

#### 服务端事件（JSON 格式）

**1. session.created - 会话创建**

```json
{
  "header": {
    "event": "session.created",
    "task_id": "uuid-string"
  },
  "payload": {
    "session": {
      "id": "session-id",
      "model": "qwen3-asr-flash-realtime"
    }
  }
}
```

**2. conversation.item.input_audio_transcription.text - 中间识别结果**

```json
{
  "header": {
    "event": "conversation.item.input_audio_transcription.text",
    "task_id": "uuid-string"
  },
  "payload": {
    "transcript": "你好",
    "is_final": false
  }
}
```

**3. conversation.item.input_audio_transcription.completed - 最终识别结果**

```json
{
  "header": {
    "event": "conversation.item.input_audio_transcription.completed",
    "task_id": "uuid-string"
  },
  "payload": {
    "transcript": "你好，今天天气怎么样？",
    "confidence": 0.95,
    "is_final": true
  }
}
```

**4. input_audio_buffer.speech_started - 语音开始**

```json
{
  "header": {
    "event": "input_audio_buffer.speech_started",
    "task_id": "uuid-string"
  }
}
```

**5. input_audio_buffer.speech_stopped - 语音结束**

```json
{
  "header": {
    "event": "input_audio_buffer.speech_stopped",
    "task_id": "uuid-string"
  }
}
```

**6. task-failed - 任务失败**

```json
{
  "header": {
    "event": "task-failed",
    "task_id": "uuid-string",
    "error_code": "CLIENT_ERROR",
    "error_message": "request timeout after 23 seconds."
  }
}
```

### 7. Python SDK 使用示例

#### 安装 SDK

```bash
pip install dashscope>=1.25.3
```

#### 基础实时识别示例

```python
import os
import dashscope
from dashscope.audio.qwen_omni import OmniRealtimeConversation
from dashscope.audio.qwen_omni import OmniRealtimeCallback

# 配置 API Key
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 自定义回调类
class MyASRCallback(OmniRealtimeCallback):
    def on_session_created(self, event):
        """会话创建"""
        print(f"会话创建: {event}")

    def on_input_audio_transcription_completed(self, event):
        """最终识别结果"""
        transcript = event.get('payload', {}).get('transcript', '')
        print(f"[最终结果] {transcript}")

    def on_input_audio_transcription_text(self, event):
        """中间识别结果"""
        transcript = event.get('payload', {}).get('transcript', '')
        is_final = event.get('payload', {}).get('is_final', False)
        print(f"[中间结果] {transcript} (final: {is_final})")

    def on_speech_started(self, event):
        """检测到语音开始"""
        print("[VAD] 语音开始")

    def on_speech_stopped(self, event):
        """检测到语音结束"""
        print("[VAD] 语音结束")

    def on_error(self, error):
        """错误处理"""
        print(f"[错误] {error}")

# 创建实时对话实例
callback = MyASRCallback()
conversation = OmniRealtimeConversation(
    model="qwen3-asr-flash-realtime",
    callback=callback
)

# 开始会话
conversation.start()

# 发送音频数据（PCM 格式，16kHz，单声道，16-bit）
with open("audio.pcm", "rb") as f:
    while True:
        chunk = f.read(3200)  # 每次读取 100ms 的音频（16000 * 2 / 10）
        if not chunk:
            break
        conversation.send_audio(chunk)

# 结束会话
conversation.finish()
```

#### 从麦克风实时识别

```python
import pyaudio
import os
import dashscope
from dashscope.audio.qwen_omni import OmniRealtimeConversation
from dashscope.audio.qwen_omni import OmniRealtimeCallback

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

class MyASRCallback(OmniRealtimeCallback):
    def on_input_audio_transcription_completed(self, event):
        transcript = event.get('payload', {}).get('transcript', '')
        print(f"\n识别结果: {transcript}")

# 音频参数
RATE = 16000
CHUNK = 1600  # 100ms

# 初始化 PyAudio
audio = pyaudio.PyAudio()
stream = audio.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

# 创建实时识别会话
callback = MyASRCallback()
conversation = OmniRealtimeConversation(
    model="qwen3-asr-flash-realtime",
    callback=callback
)

print("开始录音，按 Ctrl+C 停止...")
conversation.start()

try:
    while True:
        data = stream.read(CHUNK)
        conversation.send_audio(data)
except KeyboardInterrupt:
    print("\n停止录音")
finally:
    conversation.finish()
    stream.stop_stream()
    stream.close()
    audio.terminate()
```

### 8. 语言支持

#### 中文方言

- 普通话
- 粤语
- 四川话
- 闽南语
- 吴语

#### 国际语言（11种）

- 中文 (Chinese)
- 英语 (English) - 支持英式、美式等多种口音
- 法语 (French)
- 德语 (German)
- 俄语 (Russian)
- 意大利语 (Italian)
- 西班牙语 (Spanish)
- 葡萄牙语 (Portuguese)
- 日语 (Japanese)
- 韩语 (Korean)
- 阿拉伯语 (Arabic)

#### 自动语种检测

模型支持自动检测输入音频的语言，无需手动指定。

### 9. 高级配置参数

```python
conversation = OmniRealtimeConversation(
    model="qwen3-asr-flash-realtime",
    callback=callback,
    # 可选配置
    asr_options={
        "language": "auto",      # 语言：auto（自动检测）、zh（中文）、en（英语）
        "enable_itn": True,      # 是否启用逆文本归一化（如"一百"转为"100"）
        "enable_punctuation": True,  # 是否添加标点符号
        "sample_rate": 16000     # 音频采样率
    }
)
```

---

## 语音合成 (TTS) 服务

### 1. 服务概述

阿里云 DashScope 提供多个语音合成服务：

| 服务名称 | 模型代码 | 适用场景 |
|---------|---------|---------|
| **CosyVoice-v2** | `cosyvoice-v2` | 最新一代生成式语音合成（推荐） |
| **Qwen3-TTS-Flash-Realtime** | `qwen3-tts-flash-realtime` | 通义千问实时语音合成 |
| **Sambert** | `sambert-*` | 传统语音合成 |

本文档重点介绍 **CosyVoice-v2** 和 **Qwen3-TTS-Flash-Realtime**。

### 2. CosyVoice-v2 语音合成

#### 模型特点

- **生成式语音大模型**：基于通义实验室的预训练语言模型
- **流式输入输出**：支持实时合成 LLM 流式生成的文本
- **超低延迟**：首包延迟仅 150 毫秒
- **高音质**：MOS 评分 5.53，超越部分商业系统
- **低错误率**：发音错误率比前代降低 30-50%

#### WebSocket 接口地址

- **北京地域**：`wss://dashscope.aliyuncs.com/api-ws/v1/inference/`
- **新加坡地域**：`wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference/`

#### 模型版本

- `cosyvoice-v2` - 稳定版（推荐）
- `cosyvoice-v1` - 旧版本

#### 音频参数

| 参数 | 类型 | 范围 | 默认值 | 说明 |
|-----|------|------|--------|------|
| `format` | string | "mp3", "wav", "flac" | "mp3" | 音频格式 |
| `sample_rate` | int | 16000, 22050, 44100 | 22050 | 采样率（Hz） |
| `volume` | int | 0-100 | 50 | 音量 |
| `rate` | float | 0.5-2.0 | 1.0 | 语速 |
| `pitch` | float | -50 ~ 50 | 0 | 音调 |

**采样率选择建议**：
- **22050 Hz**：日常使用，平衡音质和文件大小
- **44100 Hz**：专业制作，高音质

#### 音色列表（部分）

- `longxiaochun_v2` - 龙小春（女声）
- `longyuan_v2` - 龙渊（男声）
- `longwan_v2` - 龙婉（女声）
- 更多音色请参考官方文档

### 3. Python SDK 使用示例

#### 安装 SDK

```bash
pip install dashscope>=1.24.6
```

#### 非流式合成（同步调用）

```python
import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

# 配置 API Key
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 模型和音色
model = "cosyvoice-v2"
voice = "longxiaochun_v2"

# 实例化合成器
synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    format="mp3",
    sample_rate=22050,
    volume=50,
    rate=1.0,
    pitch=0
)

# 合成语音（返回二进制音频数据）
audio = synthesizer.call("今天天气怎么样？")

# 打印性能指标
print(f'[性能指标]')
print(f'  Request ID: {synthesizer.get_last_request_id()}')
print(f'  首包延迟: {synthesizer.get_first_package_delay()} 毫秒')

# 保存音频文件
with open('output.mp3', 'wb') as f:
    f.write(audio)
    print(f'音频已保存: output.mp3')
```

#### 流式合成（异步回调）

```python
import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 自定义回调类
class MyTTSCallback(ResultCallback):
    def on_open(self):
        """WebSocket 连接建立"""
        self.file = open("output.mp3", "wb")
        print("WebSocket 连接已建立")

    def on_complete(self):
        """合成任务完成"""
        print("语音合成完成")

    def on_error(self, message: str):
        """任务失败"""
        print(f"合成失败: {message}")

    def on_close(self):
        """WebSocket 连接关闭"""
        print("WebSocket 连接已关闭")
        self.file.close()

    def on_event(self, message):
        """接收事件消息"""
        print(f"收到事件: {message}")

    def on_data(self, data: bytes) -> None:
        """接收音频数据（流式）"""
        print(f"收到音频片段: {len(data)} 字节")
        self.file.write(data)

# 创建合成器实例（流式模式）
callback = MyTTSCallback()
synthesizer = SpeechSynthesizer(
    model="cosyvoice-v2",
    voice="longxiaochun_v2",
    callback=callback
)

# 发送文本进行合成（流式输出）
synthesizer.call("今天天气怎么样？明天会下雨吗？")
```

#### 全双工流式合成（实时文本输入 + 流式音频输出）

```python
import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

class StreamingCallback(ResultCallback):
    def on_data(self, data: bytes) -> None:
        # 实时处理音频数据（如播放、保存等）
        print(f"收到 {len(data)} 字节音频")

callback = StreamingCallback()
synthesizer = SpeechSynthesizer(
    model="cosyvoice-v2",
    voice="longxiaochun_v2",
    callback=callback,
    streaming=True  # 启用全双工流式模式
)

# 模拟 LLM 流式输出文本
llm_outputs = [
    "今天",
    "天气",
    "怎么样？",
    "明天",
    "会下雨吗？"
]

# 逐步发送文本，服务端实时合成并返回音频
for text_chunk in llm_outputs:
    synthesizer.streaming_call(text_chunk)

# 完成输入
synthesizer.streaming_complete()
```

#### 高并发场景优化（连接池）

```python
import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizerObjectPool

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 创建对象池（最多 20 个复用连接）
synthesizer_pool = SpeechSynthesizerObjectPool(max_size=20)

# 从池中获取合成器
synthesizer = synthesizer_pool.get(
    model="cosyvoice-v2",
    voice="longxiaochun_v2"
)

# 使用合成器
audio = synthesizer.call("你好，世界！")

# 将合成器归还到池中（复用连接）
synthesizer_pool.release(synthesizer)
```

### 4. Qwen3-TTS-Flash-Realtime 语音合成

#### 模型版本

- `qwen3-tts-flash-realtime` - 稳定版
- `qwen3-tts-flash-realtime-2025-11-27` - 最新快照版
- `qwen3-tts-flash-realtime-2025-09-18` - 快照版

#### 特点

- **超低延迟**：适合实时交互场景
- **流式输入输出**：支持边输入边合成
- **可调参数**：支持调节语速、语调、音量、码率
- **多格式支持**：兼容主流音频格式
- **高采样率**：最高支持 48kHz 采样率

#### 使用示例

```python
import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

synthesizer = SpeechSynthesizer(
    model="qwen3-tts-flash-realtime",
    voice="default",  # 使用默认音色
    sample_rate=48000,  # 高采样率
    format="wav"
)

audio = synthesizer.call("通义千问实时语音合成测试")

with open('qwen_tts_output.wav', 'wb') as f:
    f.write(audio)
```

### 5. 文本长度限制

| 调用方式 | 单次文本长度 | 累计文本长度 |
|---------|-------------|-------------|
| 非流式调用 | ≤ 2000 字符 | N/A |
| 流式调用 | ≤ 2000 字符 | ≤ 200,000 字符 |

### 6. WebSocket 事件格式（CosyVoice）

#### 任务启动事件

```json
{
  "header": {
    "task_id": "uuid-string",
    "event": "task-started",
    "attributes": {}
  }
}
```

#### 音频数据事件

服务端通过 WebSocket 推送二进制音频数据（非 JSON 格式）。

#### 任务完成事件

```json
{
  "header": {
    "task_id": "uuid-string",
    "event": "task-finished",
    "attributes": {}
  },
  "payload": {
    "output": {
      "audio_length": 12345,
      "audio_format": "mp3"
    },
    "usage": {
      "characters": 10
    }
  }
}
```

#### 任务失败事件

```json
{
  "header": {
    "task_id": "uuid-string",
    "event": "task-failed",
    "error_code": "CLIENT_ERROR",
    "error_message": "Invalid input format",
    "attributes": {}
  }
}
```

### 7. 注意事项

1. **音频格式一致性**：确保请求参数中的 `format` 与文件后缀一致
2. **播放器兼容性**：确认播放器支持该音频格式和采样率
3. **连接复用**：WebSocket 连接可复用，避免频繁建立连接
4. **错误处理**：实现完整的错误处理逻辑，处理网络异常和超时

---

## 附录：参考资源

### 官方文档

#### 语音识别 (ASR)

1. [实时语音识别（Qwen-ASR-Realtime）Python SDK](https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-python-sdk)
2. [DashScope WebSocket API - Fun-ASR 实时语音识别](https://help.aliyun.com/zh/model-studio/fun-asr-realtime-websocket-api)
3. [实时语音识别 API 交互协议与模式](https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-interaction-process)
4. [录音文件识别内容分析](https://help.aliyun.com/zh/model-studio/qwen-speech-recognition)

#### 语音合成 (TTS)

1. [实时语音合成 - 通义千问](https://help.aliyun.com/zh/model-studio/qwen-tts-realtime)
2. [CosyVoice 快速开始](https://help.aliyun.com/zh/dashscope/developer-reference/cosyvoice-quick-start)
3. [CosyVoice Python SDK](https://help.aliyun.com/zh/model-studio/cosyvoice-python-sdk)
4. [CosyVoice WebSocket API](https://help.aliyun.com/zh/model-studio/developer-reference/cosyvoice-websocket-api)
5. [Qwen-TTS API](https://help.aliyun.com/zh/model-studio/qwen-tts-api)

#### API 认证与配置

1. [通义千问 API 调用快速入门](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)
2. [配置 API Key 到环境变量](https://help.aliyun.com/zh/model-studio/configure-api-key-through-environment-variables)
3. [DashScope API 参考](https://help.aliyun.com/zh/model-studio/dashscope-api-reference/)

### GitHub 仓库

1. [DashScope Python SDK](https://github.com/dashscope/dashscope-sdk-python)
2. [Qwen3-ASR-Toolkit](https://github.com/QwenLM/Qwen3-ASR-Toolkit)

### 技术博客

1. [阿里云 CosyVoice 语音合成大模型 API 实践](https://blog.csdn.net/qq_42586468/article/details/140044350)
2. [实测 Qwen3-ASR-Flash：完整调用教程 + 避坑指南](https://blog.csdn.net/zlututubj/article/details/151558119)
3. [阿里云获取 DASHSCOPE_API_KEY 教程](https://blog.csdn.net/weixin_44060488/article/details/148843106)

### 控制台链接

- [DashScope 控制台（北京）](https://dashscope.aliyun.com/)
- [API Key 管理（北京）](https://dashscope.console.aliyun.com/apiKey)

---

## 快速开始 Checklist

- [ ] 获取 DashScope API Key
- [ ] 配置 `DASHSCOPE_API_KEY` 环境变量
- [ ] 安装 DashScope Python SDK：`pip install dashscope>=1.25.3`
- [ ] 测试 ASR 实时语音识别功能
- [ ] 测试 TTS 语音合成功能
- [ ] 实现错误处理和重连机制
- [ ] 优化音频参数（采样率、格式、音色）
- [ ] 在生产环境部署前进行压力测试

---

**文档维护**：本文档基于 2026-01-07 的官方文档整理，如有更新请参考最新官方文档。
