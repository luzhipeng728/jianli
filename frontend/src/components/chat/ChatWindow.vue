<template>
  <div class="flex flex-col h-full">
    <!-- 消息列表 -->
    <div ref="messagesRef" class="flex-1 overflow-y-auto p-4 bg-gray-50">
      <MessageBubble
        v-for="(msg, idx) in messages"
        :key="idx"
        :message="msg"
        :metrics="idx === messages.length - 1 ? lastMetrics : undefined"
      />

      <!-- 加载中 -->
      <div v-if="loading" class="flex justify-start mb-4">
        <div class="bg-white border shadow-sm px-4 py-2 rounded-lg">
          <span class="typing-dots">正在思考</span>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="p-4 bg-white border-t">
      <div class="flex gap-2">
        <el-input
          v-model="inputText"
          placeholder="输入问题..."
          @keyup.enter="handleSend"
          :disabled="loading"
        />
        <el-button
          type="primary"
          @click="handleSend"
          :loading="loading"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { chatStream, type ChatMessage, type StreamChunk } from '@/api/chat'

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const sessionId = ref<string>()
const lastMetrics = ref<StreamChunk['metrics']>()
const messagesRef = ref<HTMLElement>()

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const handleSend = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  // 添加助手消息占位
  const assistantIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

  try {
    for await (const chunk of chatStream(text, sessionId.value)) {
      if (chunk.type === 'text') {
        messages.value[assistantIdx].content += chunk.content || ''
        scrollToBottom()
      } else if (chunk.type === 'done') {
        lastMetrics.value = chunk.metrics
        sessionId.value = chunk.metrics?.session_id
      }
    }
  } catch (e) {
    messages.value[assistantIdx].content = '抱歉，发生了错误，请重试。'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.typing-dots::after {
  content: '...';
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}
</style>
