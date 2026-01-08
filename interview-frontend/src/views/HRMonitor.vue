<template>
  <div class="h-screen bg-gray-50 flex">
    <!-- Left: Active sessions list -->
    <div class="w-72 bg-white border-r flex flex-col">
      <div class="p-4 border-b">
        <h2 class="text-lg font-semibold">实时面试监控</h2>
        <p class="text-sm text-gray-500 mt-1">{{ activeSessions.length }} 场进行中</p>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div v-for="session in activeSessions" :key="session.session_id"
          @click="watchSession(session.session_id)"
          class="p-4 border-b cursor-pointer hover:bg-gray-50 transition-colors"
          :class="{'bg-blue-50': watchingId === session.session_id}">
          <div class="font-medium text-gray-900">{{ session.session_id.slice(0, 8) }}...</div>
          <div class="text-sm text-gray-600 mt-1">
            {{ phaseNames[session.current_phase] || session.current_phase }}
          </div>
          <div class="flex items-center mt-2 text-xs text-gray-400">
            <span class="w-2 h-2 rounded-full bg-green-500 mr-1.5 animate-pulse"></span>
            进行中
          </div>
        </div>
        <div v-if="activeSessions.length === 0" class="p-8 text-center text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <p>暂无进行中的面试</p>
        </div>
      </div>
    </div>

    <!-- Main: Live interview view -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <div v-if="!watchingId" class="flex-1 flex items-center justify-center text-gray-400">
        <div class="text-center">
          <svg class="w-16 h-16 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
          </svg>
          <p>选择一场面试进行观看</p>
        </div>
      </div>

      <template v-else>
        <!-- Header with status and controls -->
        <div class="bg-white border-b p-4 shadow-sm">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-xl font-semibold text-gray-900">实时监控</h3>
              <div class="flex items-center mt-1 space-x-2">
                <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span class="text-sm text-gray-600">
                  {{ phaseNames[currentPhase] || currentPhase }} - 第 {{ currentRound + 1 }} 轮
                </span>
                <span class="text-xs text-gray-400">会话: {{ watchingId.slice(0, 12) }}...</span>
              </div>
            </div>

            <!-- Intervention controls -->
            <div class="flex space-x-2">
              <button @click="forceAdvance"
                class="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm font-medium transition-colors">
                跳过当前阶段
              </button>
              <button @click="showInjectModal = true"
                class="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 text-sm font-medium transition-colors">
                注入问题
              </button>
              <button @click="showEndModal = true"
                class="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 text-sm font-medium transition-colors">
                结束面试
              </button>
            </div>
          </div>

          <!-- Phase progress -->
          <div class="mt-4 flex space-x-1">
            <div v-for="phase in phaseOrder" :key="phase"
              class="flex-1 h-2 rounded-full transition-all"
              :class="{
                'bg-green-500': phaseOrder.indexOf(phase) < phaseOrder.indexOf(currentPhase),
                'bg-blue-500': phase === currentPhase,
                'bg-gray-200': phaseOrder.indexOf(phase) > phaseOrder.indexOf(currentPhase)
              }"
              :title="phaseNames[phase]">
            </div>
          </div>
        </div>

        <!-- Live dialogue -->
        <div ref="dialogueContainer" class="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
          <div v-if="liveDialogues.length === 0" class="h-full flex items-center justify-center text-gray-400">
            <div class="text-center">
              <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
              </svg>
              <p>等待对话开始...</p>
            </div>
          </div>

          <div v-for="msg in liveDialogues" :key="msg.id"
            class="flex" :class="msg.role === 'candidate' ? 'justify-end' : 'justify-start'">
            <div class="max-w-[80%] rounded-xl px-4 py-2 shadow-sm"
              :class="dialogueClass(msg.role)">
              <div class="text-xs mb-1" :class="msg.role === 'candidate' ? 'text-blue-200' : 'text-gray-400'">
                {{ roleText(msg.role) }}
              </div>
              <p class="whitespace-pre-wrap">{{ msg.content }}</p>
              <div class="text-xs mt-1 opacity-75">
                {{ formatTime(msg.timestamp) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Connection status -->
        <div class="bg-white border-t px-4 py-2 text-sm flex items-center justify-between"
          :class="wsConnected ? 'text-green-600' : 'text-red-600'">
          <div class="flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full" :class="wsConnected ? 'bg-green-500' : 'bg-red-500'"></span>
            <span>{{ wsConnected ? 'WebSocket 已连接' : '连接断开，正在重连...' }}</span>
          </div>
          <div class="text-gray-500">
            已接收 {{ liveDialogues.length }} 条消息
          </div>
        </div>
      </template>
    </div>

    <!-- Inject question modal -->
    <div v-if="showInjectModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showInjectModal = false">
      <div class="bg-white rounded-xl p-6 w-96 shadow-2xl">
        <h3 class="text-lg font-semibold mb-4">注入问题</h3>
        <textarea v-model="injectQuestion" rows="3"
          class="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          placeholder="输入要注入的问题..."></textarea>
        <div class="flex justify-end space-x-2 mt-4">
          <button @click="showInjectModal = false"
            class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            取消
          </button>
          <button @click="doInjectQuestion"
            class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
            发送
          </button>
        </div>
      </div>
    </div>

    <!-- End interview modal -->
    <div v-if="showEndModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showEndModal = false">
      <div class="bg-white rounded-xl p-6 w-96 shadow-2xl">
        <h3 class="text-lg font-semibold mb-4 text-red-700">结束面试</h3>
        <p class="text-sm text-gray-600 mb-4">确定要强制结束这场面试吗？此操作不可撤销。</p>
        <input v-model="endReason" class="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-red-500 focus:border-transparent"
          placeholder="结束原因 (可选)">
        <div class="flex justify-end space-x-2 mt-4">
          <button @click="showEndModal = false"
            class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            取消
          </button>
          <button @click="doForceEnd"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
            确认结束
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

// Types
interface ActiveSession {
  session_id: string
  current_phase: string
  current_round: number
  candidate_name?: string
  position?: string
}

interface DialogueMessage {
  id: string
  role: 'candidate' | 'interviewer' | 'system'
  content: string
  timestamp: string
}

// State
const activeSessions = ref<ActiveSession[]>([])
const watchingId = ref<string>('')
const currentPhase = ref<string>('opening')
const currentRound = ref<number>(0)
const liveDialogues = ref<DialogueMessage[]>([])
const wsConnected = ref<boolean>(false)
const showInjectModal = ref<boolean>(false)
const showEndModal = ref<boolean>(false)
const injectQuestion = ref<string>('')
const endReason = ref<string>('')

// WebSocket
let ws: WebSocket | null = null
let reconnectTimer: number | null = null
let pollTimer: number | null = null

// DOM refs
const dialogueContainer = ref<HTMLElement>()

// Constants
const phaseOrder = ['opening', 'self_intro', 'project_deep', 'tech_assess', 'behavioral', 'qa', 'closing']
const phaseNames: Record<string, string> = {
  'opening': '开场',
  'self_intro': '自我介绍',
  'project_deep': '项目深挖',
  'tech_assess': '技术评估',
  'behavioral': '行为面试',
  'qa': '自由问答',
  'closing': '结束'
}

// Fetch active sessions
const fetchActiveSessions = async () => {
  try {
    // Mock API - replace with actual endpoint
    const response = await fetch('/api/interview/active-sessions')
    if (response.ok) {
      const data = await response.json()
      activeSessions.value = data.data || []
    }
  } catch (error) {
    console.error('Failed to fetch active sessions:', error)
    // Mock data for development
    activeSessions.value = []
  }
}

// Watch a session
const watchSession = (sessionId: string) => {
  if (watchingId.value === sessionId) return

  // Disconnect from previous session
  if (ws) {
    ws.close()
    ws = null
  }

  watchingId.value = sessionId
  liveDialogues.value = []
  connectToSession(sessionId)
}

// Connect to WebSocket
const connectToSession = (sessionId: string) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/hr-monitor/${sessionId}`

  console.log('Connecting to HR monitor WebSocket:', wsUrl)

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('HR monitor WebSocket connected')
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    handleWebSocketMessage(event.data)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    wsConnected.value = false
  }

  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason)
    wsConnected.value = false

    // Auto reconnect if watching a session
    if (watchingId.value && !reconnectTimer) {
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null
        if (watchingId.value) {
          console.log('Reconnecting...')
          connectToSession(watchingId.value)
        }
      }, 3000)
    }
  }
}

// Handle WebSocket messages
const handleWebSocketMessage = (data: string) => {
  try {
    const message = JSON.parse(data)
    console.log('HR monitor message:', message.type)

    switch (message.type) {
      case 'subscribed':
        handleSubscribed(message)
        break

      case 'phase_change':
        handlePhaseChange(message)
        break

      case 'dialogue':
        handleDialogue(message)
        break

      case 'interview_complete':
        handleInterviewComplete(message)
        break

      case 'error':
        handleError(message)
        break
    }
  } catch (error) {
    console.error('Failed to parse WebSocket message:', error)
  }
}

// Handle subscribed message
const handleSubscribed = (message: any) => {
  currentPhase.value = message.current_phase || 'opening'
  currentRound.value = message.current_round || 0
  console.log('Subscribed to session:', message.session_id, 'phase:', currentPhase.value)
}

// Handle phase change
const handlePhaseChange = (message: any) => {
  currentPhase.value = message.phase || message.current_phase || currentPhase.value
  currentRound.value = message.round || message.current_round || currentRound.value

  // Add system message
  liveDialogues.value.push({
    id: Date.now().toString() + Math.random(),
    role: 'system',
    content: `阶段变更: ${phaseNames[currentPhase.value] || currentPhase.value}`,
    timestamp: new Date().toISOString()
  })

  scrollToBottom()
}

// Handle dialogue message
const handleDialogue = (message: any) => {
  liveDialogues.value.push({
    id: message.id || Date.now().toString() + Math.random(),
    role: message.role === 'user' ? 'candidate' : (message.role === 'assistant' ? 'interviewer' : message.role),
    content: message.content || message.text || '',
    timestamp: message.timestamp || new Date().toISOString()
  })

  scrollToBottom()
}

// Handle interview complete
const handleInterviewComplete = (message: any) => {
  const evaluation = message.evaluation || {}
  const score = evaluation.overall_score || 'N/A'
  const recommendation = evaluation.recommendation || 'N/A'

  liveDialogues.value.push({
    id: Date.now().toString() + Math.random(),
    role: 'system',
    content: `面试结束 - 评分: ${score}, 推荐: ${recommendation}`,
    timestamp: new Date().toISOString()
  })

  scrollToBottom()
}

// Handle error
const handleError = (message: any) => {
  console.error('Server error:', message.message)
  alert(`错误: ${message.message || '未知错误'}`)
}

// Intervention: Force advance
const forceAdvance = () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    alert('WebSocket 未连接')
    return
  }

  if (!confirm('确定要跳过当前阶段吗？')) return

  ws.send(JSON.stringify({
    type: 'intervention',
    command: 'force_advance'
  }))

  console.log('Sent force_advance intervention')
}

// Intervention: Inject question
const doInjectQuestion = () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    alert('WebSocket 未连接')
    return
  }

  if (!injectQuestion.value.trim()) {
    alert('请输入问题')
    return
  }

  ws.send(JSON.stringify({
    type: 'intervention',
    command: 'inject_question',
    data: {
      question: injectQuestion.value.trim()
    }
  }))

  console.log('Sent inject_question intervention:', injectQuestion.value)

  // Add to dialogue
  liveDialogues.value.push({
    id: Date.now().toString() + Math.random(),
    role: 'system',
    content: `[HR注入问题] ${injectQuestion.value}`,
    timestamp: new Date().toISOString()
  })

  injectQuestion.value = ''
  showInjectModal.value = false
  scrollToBottom()
}

// Intervention: Force end
const doForceEnd = () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    alert('WebSocket 未连接')
    return
  }

  ws.send(JSON.stringify({
    type: 'intervention',
    command: 'force_end',
    data: {
      reason: endReason.value.trim() || 'HR强制结束'
    }
  }))

  console.log('Sent force_end intervention:', endReason.value)

  endReason.value = ''
  showEndModal.value = false
}

// Helper: Dialogue class
const dialogueClass = (role: string) => {
  if (role === 'candidate') {
    return 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white'
  } else if (role === 'interviewer') {
    return 'bg-white text-gray-800 border border-gray-200'
  } else {
    return 'bg-gray-100 text-gray-600 border border-gray-200'
  }
}

// Helper: Role text
const roleText = (role: string) => {
  if (role === 'candidate') return '候选人'
  if (role === 'interviewer') return 'AI面试官'
  if (role === 'system') return '系统'
  return role
}

// Helper: Format time
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Helper: Scroll to bottom
const scrollToBottom = async () => {
  await nextTick()
  if (dialogueContainer.value) {
    dialogueContainer.value.scrollTop = dialogueContainer.value.scrollHeight
  }
}

// Lifecycle
onMounted(() => {
  // Fetch active sessions immediately
  fetchActiveSessions()

  // Poll for active sessions every 5 seconds
  pollTimer = window.setInterval(() => {
    fetchActiveSessions()
  }, 5000)
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>
