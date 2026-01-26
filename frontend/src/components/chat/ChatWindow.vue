<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- Messages Area -->
    <div ref="messagesRef" class="flex-1 overflow-y-auto p-6 bg-secondary-50/50 min-h-0">
      <!-- Welcome Message -->
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-center">
        <div class="w-20 h-20 rounded-2xl bg-primary-50 flex items-center justify-center mb-4">
          <svg class="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-secondary-800 mb-2">开始对话</h3>
        <p class="text-secondary-500 max-w-md">
          向AI助手询问关于简历库的问题，例如：<br/>
          "帮我找一个有Python经验的候选人"
        </p>
        <!-- Quick Actions -->
        <div class="flex flex-wrap gap-2 mt-6 justify-center">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            @click="handleSuggestion(suggestion)"
            class="px-4 py-2 rounded-full bg-white border border-secondary-200 text-sm text-secondary-600 hover:border-primary-300 hover:text-primary-600 transition-colors cursor-pointer"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <!-- Message List -->
      <div v-else class="space-y-6">
        <MessageBubble
          v-for="(msg, idx) in messages"
          :key="idx"
          :message="msg"
          :metrics="idx === messages.length - 1 ? lastMetrics : undefined"
          @candidate-click="handleCandidateClick"
        />

        <!-- Loading State -->
        <div v-if="loading" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div class="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-secondary-100">
            <div class="flex items-center gap-2">
              <div class="flex gap-1">
                <span class="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style="animation-delay: 300ms"></span>
              </div>
              <span class="text-sm text-secondary-500">正在思考</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="p-4 bg-white border-t border-secondary-100 flex-shrink-0">
      <div class="flex gap-3 items-end">
        <div class="flex-1 relative">
          <textarea
            v-model="inputText"
            @keydown.enter.exact.prevent="handleSend"
            :disabled="loading"
            placeholder="输入您的问题..."
            rows="1"
            class="input-field resize-none min-h-[44px] max-h-[120px] pr-12"
            :style="{ height: textareaHeight }"
            @input="adjustTextarea"
          />
          <button
            @click="handleSend"
            :disabled="loading || !inputText.trim()"
            class="absolute right-2 bottom-2 w-8 h-8 rounded-lg flex items-center justify-center transition-all"
            :class="inputText.trim() && !loading
              ? 'bg-primary-600 text-white hover:bg-primary-700'
              : 'bg-secondary-100 text-secondary-400 cursor-not-allowed'"
          >
            <svg v-if="!loading" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            <div v-else class="w-4 h-4 border-2 border-secondary-300 border-t-primary-600 rounded-full animate-spin"></div>
          </button>
        </div>
      </div>
      <p class="text-xs text-secondary-400 mt-2 text-center">
        按 Enter 发送消息，Shift + Enter 换行
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { chatStream, type ChatMessage, type StreamChunk, type CardData } from '@/api/chat'

const props = defineProps<{
  jdId?: string
}>()

const emit = defineEmits<{
  candidateClick: [candidate: any]
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const sessionId = ref<string>()
const lastMetrics = ref<StreamChunk['metrics']>()
const messagesRef = ref<HTMLElement>()
const textareaHeight = ref('44px')

const suggestions = [
  '查找有Python经验的候选人',
  '找出学历在本科以上的简历',
  '搜索5年以上工作经验的人才',
]

const adjustTextarea = (event: Event) => {
  const target = event.target as HTMLTextAreaElement
  target.style.height = '44px'
  target.style.height = Math.min(target.scrollHeight, 120) + 'px'
  textareaHeight.value = target.style.height
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const handleSuggestion = (text: string) => {
  inputText.value = text
  handleSend()
}

const handleCandidateClick = (candidate: any) => {
  emit('candidateClick', candidate)
}

const handleSend = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  // Add user message
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  textareaHeight.value = '44px'
  loading.value = true
  scrollToBottom()

  // Add assistant message placeholder
  const assistantIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

  try {
    for await (const chunk of chatStream(text, sessionId.value, false, props.jdId)) {
      const msg = messages.value[assistantIdx]
      if (!msg) continue

      if (chunk.type === 'text') {
        msg.content += chunk.content || ''
        scrollToBottom()
      } else if (chunk.type === 'card') {
        // 添加卡片数据
        if (!msg.cards) msg.cards = []
        msg.cards.push({
          type: chunk.card_type as CardData['type'],
          data: chunk.data
        })
        scrollToBottom()
      } else if (chunk.type === 'done') {
        lastMetrics.value = chunk.metrics
        sessionId.value = chunk.metrics?.session_id
      }
    }
  } catch (e) {
    const msg = messages.value[assistantIdx]
    if (msg) {
      msg.content = '抱歉，发生了错误，请重试。'
    }
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.animate-bounce {
  animation: bounce 0.6s infinite;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
