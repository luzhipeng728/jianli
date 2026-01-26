<template>
  <div class="h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex flex-col overflow-hidden">
    <!-- 未开始状态 - 欢迎页 -->
    <div v-if="!isStarted" class="flex-1 flex items-center justify-center p-4">
      <div class="w-full max-w-lg">
        <div class="bg-white/70 backdrop-blur-xl rounded-3xl shadow-xl border border-white/50 p-8 text-center">
          <!-- Logo动画 -->
          <div class="relative w-32 h-32 mx-auto mb-6">
            <div class="absolute inset-0 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full animate-pulse"></div>
            <div class="absolute inset-2 bg-white rounded-full flex items-center justify-center">
              <svg class="w-12 h-12 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path>
              </svg>
            </div>
          </div>

          <h1 class="text-2xl font-bold text-gray-900 mb-2">AI 语音面试</h1>
          <p class="text-gray-600 mb-6">准备好后点击开始，AI面试官将与您实时对话</p>

          <div class="bg-blue-50 rounded-2xl p-4 mb-6 text-left">
            <div class="flex items-start space-x-3 mb-3">
              <svg class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
              </svg>
              <span class="text-gray-700 text-sm">确保麦克风和扬声器正常工作</span>
            </div>
            <div class="flex items-start space-x-3 mb-3">
              <svg class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
              </svg>
              <span class="text-gray-700 text-sm">保持安静的环境以获得最佳体验</span>
            </div>
            <div class="flex items-start space-x-3">
              <svg class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
              </svg>
              <span class="text-gray-700 text-sm">说完后点击<strong>发送回答</strong>按钮提交</span>
            </div>
          </div>

          <button
            @click="startInterview"
            :disabled="isConnecting"
            class="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-2xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            <span v-if="isConnecting" class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              正在连接...
            </span>
            <span v-else class="flex items-center justify-center">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              开始面试
            </span>
          </button>

          <p v-if="connectionError" class="mt-4 text-red-500 text-sm">{{ connectionError }}</p>
        </div>
      </div>
    </div>

    <!-- 面试进行中 -->
    <template v-else>
      <!-- 顶部状态栏 -->
      <div class="flex-shrink-0 bg-white/70 backdrop-blur-xl border-b border-white/50 px-4 py-3">
        <div class="max-w-4xl mx-auto flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-2 h-2 rounded-full animate-pulse" :class="interviewStatus === 'stopped' ? 'bg-gray-400' : 'bg-green-500'"></div>
            <span class="font-medium text-gray-900">AI 语音面试</span>
            <span class="text-sm px-2 py-0.5 rounded-full" :class="statusBadgeClass">{{ statusText }}</span>

            <!-- Phase Progress -->
            <div v-if="currentPhase" class="flex items-center space-x-2 ml-4">
              <div class="flex space-x-1">
                <div v-for="phase in phaseOrder" :key="phase"
                  class="w-2 h-2 rounded-full transition-all"
                  :class="{
                    'bg-green-500': phaseOrder.indexOf(phase) < phaseOrder.indexOf(currentPhase),
                    'bg-blue-500 animate-pulse': phase === currentPhase,
                    'bg-gray-300': phaseOrder.indexOf(phase) > phaseOrder.indexOf(currentPhase)
                  }"
                  :title="phaseNames[phase]"
                ></div>
              </div>
              <span class="text-sm text-gray-600">{{ phaseDescription }}</span>
              <span class="text-xs text-gray-400">({{ currentRound + 1 }}/{{ maxRounds }})</span>
            </div>
          </div>
          <div class="flex items-center space-x-4">
            <div class="text-right">
              <span class="text-2xl font-mono font-bold text-gray-900">{{ formatDuration(duration) }}</span>
            </div>
            <button
              @click="endInterview"
              class="text-gray-500 hover:text-red-500 transition-colors p-2 hover:bg-red-50 rounded-lg"
              title="结束面试"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 主内容区 -->
      <div class="flex-1 flex flex-col max-w-4xl w-full mx-auto p-4 overflow-hidden">
        <!-- AI面试官区域 -->
        <div class="flex-shrink-0 mb-4">
          <div class="bg-white/70 backdrop-blur-xl rounded-2xl border border-white/50 shadow-lg p-4">
            <div class="flex items-center space-x-4">
              <!-- AI头像 + 动效 -->
              <div class="relative flex-shrink-0">
                <div
                  class="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center transition-transform duration-300"
                  :class="{ 'scale-110': interviewStatus === 'speaking' }"
                >
                  <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                  </svg>
                </div>
                <!-- 说话动画波纹 -->
                <div v-if="interviewStatus === 'speaking'" class="absolute inset-0">
                  <div class="absolute inset-0 rounded-full bg-blue-400 animate-ping opacity-30"></div>
                  <div class="absolute inset-0 rounded-full bg-blue-400 animate-ping opacity-20" style="animation-delay: 0.2s"></div>
                </div>
              </div>

              <!-- AI状态信息 -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center space-x-2">
                  <h3 class="font-semibold text-gray-900">AI 面试官</h3>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="aiStatusBadgeClass">
                    {{ aiStatusText }}
                  </span>
                </div>

                <!-- 声波动画 -->
                <div v-if="interviewStatus === 'speaking'" class="flex items-center space-x-1 mt-2 h-6">
                  <div v-for="i in 12" :key="i"
                    class="w-1 bg-gradient-to-t from-blue-500 to-indigo-500 rounded-full sound-wave"
                    :style="{ animationDelay: `${i * 0.05}s` }"
                  ></div>
                </div>
                <p v-else-if="interviewStatus === 'processing'" class="text-sm text-yellow-600 mt-2 flex items-center">
                  <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  正在思考...
                </p>
                <p v-else class="text-sm text-gray-500 mt-2">等待您的回答</p>
              </div>

              <!-- 跳过按钮 - 面试官说话时显示 -->
              <button
                v-if="interviewStatus === 'speaking'"
                @click="skipAudio"
                class="flex-shrink-0 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2 animate-pulse"
                title="跳过当前语音"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"></path>
                </svg>
                <span>跳过语音</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 对话区域 -->
        <div class="flex-1 min-h-0 mb-4">
          <div class="h-full bg-white/70 backdrop-blur-xl rounded-2xl border border-white/50 shadow-lg overflow-hidden">
            <div ref="messagesContainer" class="h-full overflow-y-auto p-4 space-y-3">
              <!-- 分析进度显示 -->
              <div v-if="interviewStatus === 'analyzing'" class="h-full flex items-center justify-center p-4">
                <div class="w-full max-w-md">
                  <div class="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-6 border border-purple-100">
                    <!-- 动画图标 -->
                    <div class="flex justify-center mb-4">
                      <div class="relative">
                        <div class="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                          <svg class="w-8 h-8 text-white animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                          </svg>
                        </div>
                        <div class="absolute inset-0 rounded-full border-4 border-purple-300 animate-ping opacity-30"></div>
                      </div>
                    </div>

                    <h3 class="text-center text-lg font-semibold text-gray-800 mb-4">AI 正在准备面试</h3>

                    <!-- 分析进度文字 -->
                    <div ref="analysisProgressContainer" class="bg-white rounded-xl p-4 min-h-[120px] max-h-[200px] overflow-y-auto text-sm text-gray-600 whitespace-pre-wrap font-mono">
                      {{ analysisProgress || '正在初始化...' }}
                      <span class="inline-block w-2 h-4 bg-purple-500 animate-pulse ml-1"></span>
                    </div>

                    <p class="text-center text-xs text-gray-400 mt-4">正在分析岗位需求和候选人背景，生成针对性问题...</p>
                  </div>
                </div>
              </div>

              <!-- 空状态 (不在分析中且没有消息时显示) -->
              <div v-else-if="messages.length === 0 && !isAnalyzing" class="h-full flex items-center justify-center">
                <div class="text-center text-gray-400">
                  <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                  </svg>
                  <p>对话即将开始...</p>
                </div>
              </div>

              <!-- 消息列表 -->
              <template v-for="message in messages" :key="message.id">
                <!-- System message (phase changes) -->
                <div v-if="message.role === 'system'" class="flex justify-center">
                  <div class="px-4 py-1 bg-gray-100 rounded-full text-sm text-gray-500">
                    {{ message.content }}
                  </div>
                </div>

                <!-- User or assistant message -->
                <div v-else class="flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
                  <div
                    class="max-w-[85%] rounded-2xl px-4 py-2.5 shadow-sm"
                    :class="message.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-br-md'
                      : 'bg-white text-gray-800 rounded-bl-md border border-gray-100'"
                  >
                    <p class="whitespace-pre-wrap text-sm leading-relaxed">{{ message.content }}</p>
                    <p class="text-xs mt-1" :class="message.role === 'user' ? 'text-blue-100' : 'text-gray-400'">
                      {{ formatTime(message.timestamp) }}
                    </p>
                  </div>
                </div>
              </template>

              <!-- 实时转录显示 -->
              <div v-if="currentTranscript" class="flex justify-end">
                <div class="max-w-[85%] rounded-2xl px-4 py-2.5 shadow-sm bg-blue-100 text-blue-800 rounded-br-md border border-blue-200">
                  <p class="whitespace-pre-wrap text-sm leading-relaxed italic">{{ currentTranscript }}...</p>
                </div>
              </div>

              <!-- AI实时响应显示 -->
              <div v-if="currentResponse" class="flex justify-start">
                <div class="max-w-[85%] rounded-2xl px-4 py-2.5 shadow-sm bg-white text-gray-800 rounded-bl-md border border-gray-100">
                  <p class="whitespace-pre-wrap text-sm leading-relaxed">{{ currentResponse }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部控制区 -->
        <div class="flex-shrink-0">
          <div class="bg-white/80 backdrop-blur-xl rounded-2xl border border-white/50 shadow-lg p-4">
            <div class="flex items-center space-x-4">
              <!-- 麦克风状态 -->
              <div class="flex items-center space-x-3 flex-1">
                <div
                  class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300"
                  :class="micStatusClass"
                >
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"></path>
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"></path>
                  </svg>
                </div>

                <!-- 状态显示 + 音量条 + 录音时长 -->
                <div class="flex-1">
                  <div v-if="interviewStatus === 'listening'" class="space-y-2">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center space-x-2">
                        <span class="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                        <span class="text-green-600 font-medium">正在录音...</span>
                      </div>
                      <!-- 录音时长显示 -->
                      <div class="flex items-center space-x-2">
                        <span class="text-sm font-mono text-gray-600">
                          {{ formatDuration(recordingTime) }}
                        </span>
                      </div>
                    </div>
                    <!-- 音量可视化 -->
                    <div class="flex items-end space-x-0.5 h-6">
                      <div v-for="i in 20" :key="i"
                        class="w-1.5 bg-gradient-to-t from-green-500 to-emerald-400 rounded-sm transition-all duration-75"
                        :style="{ height: `${Math.min(100, Math.max(8, volumeLevel * (1 + Math.sin(i * 0.5) * 0.3)))}%` }">
                      </div>
                    </div>
                  </div>
                  <p v-else class="text-sm" :class="statusTextClass">{{ userStatusText }}</p>
                </div>
              </div>

              <!-- 发送按钮 -->
              <button
                @click="commitAudio"
                :disabled="interviewStatus !== 'listening'"
                class="flex-shrink-0 px-6 py-3 rounded-xl font-semibold transition-all duration-300 flex items-center space-x-2"
                :class="sendButtonClass"
              >
                <svg v-if="interviewStatus === 'listening'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
                </svg>
                <svg v-else-if="interviewStatus === 'speaking'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728"></path>
                </svg>
                <svg v-else class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                <span>{{ sendButtonText }}</span>
              </button>
            </div>

            <!-- 提示文字 -->
            <p v-if="interviewStatus === 'listening'" class="text-center text-xs text-gray-500 mt-3">
              说完后点击"发送回答"按钮提交，无时间限制
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { interviewApi } from '../api/interview'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

const route = useRoute()
const router = useRouter()

// 状态
const isStarted = ref(false)
const isConnecting = ref(false)
const connectionError = ref('')
// interviewStatus includes 'analyzing' for the JD analysis phase before interview starts
const interviewStatus = ref<'listening' | 'processing' | 'speaking' | 'stopped' | 'analyzing'>('stopped')
const messages = ref<Message[]>([])
const duration = ref(0)
const currentTranscript = ref('')
const currentResponse = ref('')
const analysisProgress = ref('')  // 分析进度文字
const volumeLevel = ref(0)
const audioFrameCount = ref(0)

// Phase tracking
const currentPhase = ref('')
const phaseDescription = ref('')
const currentRound = ref(0)
const maxRounds = ref(0)
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

// 录音时间（无限制，仅用于显示）
const recordingTime = ref(0)
let recordingTimer: number | null = null

// DOM引用
const messagesContainer = ref<HTMLElement>()
const analysisProgressContainer = ref<HTMLElement>()

// 计时器
let durationTimer: number | null = null
let pingTimer: number | null = null

// WebSocket
let ws: WebSocket | null = null

// 音频相关
let audioContext: AudioContext | null = null
let mediaStream: MediaStream | null = null
let audioWorkletNode: AudioWorkletNode | null = null
let audioQueue: ArrayBuffer[] = []
let isPlayingAudio = false

// 流式音频播放相关
let playbackContext: AudioContext | null = null
let nextPlayTime = 0  // 下一个音频块的播放时间
let isStreamingPlayback = false  // 是否正在流式播放
const MIN_BUFFER_SIZE = 4800  // 最小缓冲 (0.2秒 @ 24kHz)

const token = computed(() => route.params.token as string)

// 是否在分析中
const isAnalyzing = computed(() => interviewStatus.value === 'analyzing')

// 状态显示
const statusText = computed(() => {
  if (interviewStatus.value === 'analyzing') return '准备面试中...'
  if (interviewStatus.value === 'speaking') return '面试官提问中'
  if (interviewStatus.value === 'processing') return '处理中'
  if (interviewStatus.value === 'stopped') return '已结束'
  return '等待回答'
})

const statusBadgeClass = computed(() => {
  if (interviewStatus.value === 'analyzing') return 'bg-purple-100 text-purple-700'
  if (interviewStatus.value === 'speaking') return 'bg-blue-100 text-blue-700'
  if (interviewStatus.value === 'processing') return 'bg-yellow-100 text-yellow-700'
  if (interviewStatus.value === 'stopped') return 'bg-gray-100 text-gray-700'
  return 'bg-green-100 text-green-700'
})

const aiStatusText = computed(() => {
  if (interviewStatus.value === 'analyzing') return '准备问题'
  if (interviewStatus.value === 'speaking') return '正在说话'
  if (interviewStatus.value === 'processing') return '思考中'
  return '等待中'
})

const aiStatusBadgeClass = computed(() => {
  if (interviewStatus.value === 'analyzing') return 'bg-purple-100 text-purple-600'
  if (interviewStatus.value === 'speaking') return 'bg-blue-100 text-blue-600'
  if (interviewStatus.value === 'processing') return 'bg-yellow-100 text-yellow-600'
  return 'bg-gray-100 text-gray-500'
})

const micStatusClass = computed(() => {
  if (interviewStatus.value === 'analyzing') return 'bg-purple-400'
  if (interviewStatus.value === 'speaking') return 'bg-gray-400'
  if (interviewStatus.value === 'processing') return 'bg-yellow-500'
  return 'bg-green-500 animate-pulse'
})

const userStatusText = computed(() => {
  if (interviewStatus.value === 'analyzing') return 'AI 正在准备面试问题...'
  if (interviewStatus.value === 'speaking') return '请聆听面试官...'
  if (interviewStatus.value === 'processing') return '正在处理您的回答...'
  if (interviewStatus.value === 'stopped') return '面试已结束'
  return '正在录音...'
})

const statusTextClass = computed(() => {
  if (interviewStatus.value === 'analyzing') return 'text-purple-600'
  if (interviewStatus.value === 'speaking') return 'text-blue-600'
  if (interviewStatus.value === 'processing') return 'text-yellow-600'
  if (interviewStatus.value === 'stopped') return 'text-gray-500'
  return 'text-green-600'
})

const sendButtonText = computed(() => {
  if (interviewStatus.value === 'analyzing') return '准备中'
  if (interviewStatus.value === 'speaking') return '聆听中'
  if (interviewStatus.value === 'processing') return '处理中'
  return '发送回答'
})

const sendButtonClass = computed(() => {
  if (interviewStatus.value !== 'listening') {
    return 'bg-gray-200 text-gray-400 cursor-not-allowed'
  }
  return 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-lg hover:shadow-xl hover:scale-105 cursor-pointer'
})

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 滚动分析进度到底部
const scrollAnalysisToBottom = async () => {
  await nextTick()
  if (analysisProgressContainer.value) {
    analysisProgressContainer.value.scrollTop = analysisProgressContainer.value.scrollHeight
  }
}

// 会话数据
const sessionData = ref<{
  resume_id?: string
  jd_id?: string
  resume_summary?: string
  job_info?: string
  position_name?: string
  written_test_summary?: string
}>({})

// 开始面试
const startInterview = async () => {
  isConnecting.value = true
  connectionError.value = ''

  try {
    // 0. 先获取会话数据
    try {
      const response = await interviewApi.getSession(token.value)
      sessionData.value = {
        resume_id: response.data.resume_id,
        jd_id: response.data.jd_id,
        resume_summary: response.data.resume_summary || `候选人: ${response.data.candidate_name || '未知'}`,
        job_info: response.data.job_info || `职位: ${response.data.position || '技术岗位'}`,
        position_name: response.data.position || '技术岗位',
        written_test_summary: response.data.written_test_summary || ''
      }
      console.log('Resume summary:', sessionData.value.resume_summary)
      console.log('Job info:', sessionData.value.job_info)
      console.log('Position name:', sessionData.value.position_name)
      console.log('Written test summary:', sessionData.value.written_test_summary)
      console.log('Session data loaded:', sessionData.value)
    } catch (e) {
      console.warn('Failed to load session data, using defaults')
    }

    // 1. 请求麦克风权限
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      }
    })

    // 2. 初始化音频上下文
    audioContext = new AudioContext({ sampleRate: 24000 })

    // 3. 连接 WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // 使用结构化面试 WebSocket 端点，支持7阶段状态机
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/structured-interview/${token.value}`
    console.log('Connecting to:', wsUrl)

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      // Send init message with resume, job info and written test summary from session data
      ws?.send(JSON.stringify({
        type: 'init',
        resume_id: sessionData.value.resume_id || '',
        jd_id: sessionData.value.jd_id || '',
        resume_summary: sessionData.value.resume_summary || '候选人',
        job_info: sessionData.value.job_info || '技术岗位',
        position_name: sessionData.value.position_name || '技术岗位',
        written_test_summary: sessionData.value.written_test_summary || ''
      }))
      isConnecting.value = false
      isStarted.value = true
      startDurationTimer()
      startPingTimer()
      // 【重要】不在这里启动音频采集，等分析完成后再启动
      // Audio capture will be started after analysis_complete is received
      console.log('[Audio] Not starting audio capture yet - waiting for analysis to complete')
    }

    ws.onmessage = (event) => {
      handleWebSocketMessage(event.data)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      connectionError.value = '连接失败，请重试'
      isConnecting.value = false
    }

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      if (isStarted.value && interviewStatus.value !== 'stopped') {
        connectionError.value = '连接已断开'
        interviewStatus.value = 'stopped'
      }
    }

  } catch (error: any) {
    console.error('Start error:', error)
    connectionError.value = error.message || '启动失败'
    isConnecting.value = false
  }
}

// 处理 WebSocket 消息
const handleWebSocketMessage = (data: string) => {
  try {
    const message = JSON.parse(data)
    console.log('[WS] Received message:', message.type, message.text?.substring(0, 50) || '')

    switch (message.type) {
      case 'status':
        handleStatusChange(message.status)
        break

      case 'transcript':
        handleTranscript(message.text, message.is_final)
        break

      case 'response_text':
        handleResponseText(message.text)
        break

      case 'audio':
        handleAudio(message.audio)
        break

      case 'phase_start':
      case 'phase_change':
        handlePhaseChange(message)
        break

      case 'round_update':
        handleRoundUpdate(message)
        break

      case 'analysis_progress':
        handleAnalysisProgress(message.text)
        break

      case 'analysis_complete':
        handleAnalysisComplete()
        break

      case 'interview_end':
        handleInterviewEnd(message)
        break

      case 'audio_complete':
        // 后端音频流发送完成，等待前端播放完毕后切换到 listening
        handleAudioComplete()
        break

      case 'end':
        handleEnd(message.reason)
        break

      case 'error':
        handleError(message.message)
        break

      case 'pong':
        // 心跳响应
        break
    }
  } catch (e) {
    console.error('Parse message error:', e)
  }
}

// 启动录音计时器（仅用于显示录音时长，无时间限制）
const startRecordingTimer = () => {
  stopRecordingTimer()
  recordingTime.value = 0
  recordingTimer = window.setInterval(() => {
    recordingTime.value++
  }, 1000)
}

// 停止录音计时器
const stopRecordingTimer = () => {
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  recordingTime.value = 0
}

// 等待切换到 listening 的标志（后端发来 listening 但音频还在播放）
let pendingListeningStatus = false

// 处理分析进度
const handleAnalysisProgress = (text: string) => {
  console.log('[Analysis] Progress:', text)
  analysisProgress.value += text
  // 滚动分析进度容器到底部
  scrollAnalysisToBottom()
}

// 处理分析完成
const handleAnalysisComplete = () => {
  console.log('[Analysis] Complete, starting audio capture')
  // 分析完成后启动音频采集
  startAudioCapture()
  // analysisProgress 保留显示，等面试开始后再清除
}

// 处理状态变化
const handleStatusChange = (status: string) => {
  console.log('Status changed to:', status)

  if (status === 'analyzing') {
    interviewStatus.value = 'analyzing'
    pendingListeningStatus = false
    analysisProgress.value = ''  // 清空之前的分析进度
  } else if (status === 'processing') {
    interviewStatus.value = 'processing'
    pendingListeningStatus = false
    stopRecordingTimer()
  } else if (status === 'speaking') {
    interviewStatus.value = 'speaking'
    pendingListeningStatus = false
    stopRecordingTimer()
  } else if (status === 'stopped') {
    interviewStatus.value = 'stopped'
    pendingListeningStatus = false
    stopRecordingTimer()
  }
  // Note: 'listening' status is now handled by audio_complete message
}

// 切换到 listening 状态
const switchToListening = () => {
  console.log('[Status] Switching to listening')
  interviewStatus.value = 'listening'
  pendingListeningStatus = false
  // 启动录音计时器
  startRecordingTimer()
  // 完成AI响应消息
  if (currentResponse.value) {
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: currentResponse.value,
      timestamp: new Date().toISOString()
    })
    currentResponse.value = ''
    scrollToBottom()
  }
}

// 标记音频流是否已完成传输
let audioStreamComplete = false

// 处理音频流传输完成
const handleAudioComplete = () => {
  console.log('[Audio] Backend audio stream complete, queue:', audioQueue.length, 'streaming:', isStreamingPlayback)

  // 标记流传输完成
  audioStreamComplete = true
  pendingListeningStatus = true

  // 处理任何剩余的音频
  if (audioQueue.length > 0 || isStreamingPlayback) {
    if (!isStreamingPlayback) {
      // 还没开始播放，现在开始
      startStreamingPlayback()
    } else {
      // 已经在播放，处理剩余队列并等待完成
      processAudioQueue()
    }
  } else {
    // 没有音频，直接切换
    switchToListening()
  }
}

// 结束流式播放
const finishStreamingPlayback = async () => {
  // 确保队列为空
  if (audioQueue.length > 0) {
    console.log(`[Audio] Cannot finish yet, still have ${audioQueue.length} chunks`)
    return
  }

  console.log('[Audio] Finishing streaming playback')

  // 等待最后一个音频播放完成
  if (playbackContext && playbackContext.state !== 'closed') {
    const remainingTime = Math.max(0, nextPlayTime - playbackContext.currentTime)
    if (remainingTime > 0) {
      console.log(`[Audio] Waiting final ${remainingTime.toFixed(2)}s`)
      await new Promise(resolve => setTimeout(resolve, remainingTime * 1000 + 200))
    }

    try {
      await playbackContext.close()
    } catch (e) {
      console.error('Close playback context error:', e)
    }
  }
  playbackContext = null
  isStreamingPlayback = false
  audioStreamComplete = false
  nextPlayTime = 0

  // 切换到 listening 状态
  if (pendingListeningStatus) {
    switchToListening()
  }
}

// 处理转录
const handleTranscript = (text: string, isFinal: boolean) => {
  if (isFinal) {
    // 完成用户消息
    messages.value.push({
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    })
    currentTranscript.value = ''
    scrollToBottom()
  } else {
    currentTranscript.value = text
    // 流式转录时也滚动到底部
    scrollToBottom()
  }
}

// 处理响应文本
const handleResponseText = (text: string) => {
  // 收到面试官文字时，立即切换到 speaking 状态
  if (interviewStatus.value === 'listening') {
    interviewStatus.value = 'speaking'
    stopRecordingTimer()
  }

  // 如果是新的响应（上一个已经被加入消息列表），直接设置
  // 否则累加（支持流式响应）
  if (currentResponse.value === '') {
    currentResponse.value = text
  } else {
    currentResponse.value += text
  }
  scrollToBottom()
}

// 处理音频（流式播放 - 边收边播）
const handleAudio = (audioBase64: string) => {
  try {
    // 收到面试官音频时，立即切换到 speaking 状态
    if (interviewStatus.value === 'listening') {
      interviewStatus.value = 'speaking'
      stopRecordingTimer()
    }

    const binaryString = atob(audioBase64)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    audioQueue.push(bytes.buffer)

    // 【流式播放】收到数据后立即处理
    if (!isStreamingPlayback) {
      // 计算队列中总字节数
      const totalBytes = audioQueue.reduce((sum, buf) => sum + buf.byteLength, 0)
      // 有足够数据（约0.2秒）就开始播放
      if (totalBytes >= MIN_BUFFER_SIZE) {
        startStreamingPlayback()
      }
    } else {
      // 已经在播放中，处理新到的数据
      processAudioQueue()
    }
  } catch (e) {
    console.error('Audio decode error:', e)
  }
}

// 开始流式音频播放
const startStreamingPlayback = () => {
  if (isStreamingPlayback) return
  isStreamingPlayback = true
  console.log('[Audio] Starting streaming playback')

  // 创建播放用的 AudioContext
  if (!playbackContext || playbackContext.state === 'closed') {
    playbackContext = new AudioContext({ sampleRate: 24000 })
  }

  // 初始化播放时间
  nextPlayTime = playbackContext.currentTime + 0.1  // 100ms 延迟启动

  // 开始处理队列
  processAudioQueue()
}

// 处理音频队列 - 批量调度所有待播放的音频
const processAudioQueue = () => {
  if (!playbackContext || playbackContext.state === 'closed') {
    console.log('[Audio] No playback context, stopping')
    return
  }

  let scheduledCount = 0

  // 处理队列中所有可用的 chunk
  while (audioQueue.length > 0) {
    const buffer = audioQueue.shift()!

    try {
      // PCM 16-bit -> Float32
      const int16Array = new Int16Array(buffer)
      const float32Array = new Float32Array(int16Array.length)
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i]! / 32768.0
      }

      // 创建音频缓冲区
      const audioBuffer = playbackContext.createBuffer(1, float32Array.length, 24000)
      audioBuffer.getChannelData(0).set(float32Array)

      // 调度播放
      const source = playbackContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(playbackContext.destination)

      // 确保播放时间不会落后于当前时间
      const now = playbackContext.currentTime
      if (nextPlayTime < now) {
        nextPlayTime = now + 0.01
      }

      source.start(nextPlayTime)

      // 更新下一个播放时间
      const duration = float32Array.length / 24000
      nextPlayTime += duration
      scheduledCount++

    } catch (e) {
      console.error('Schedule audio error:', e)
    }
  }

  if (scheduledCount > 0) {
    const totalDuration = nextPlayTime - playbackContext.currentTime
    console.log(`[Audio] Scheduled ${scheduledCount} chunks, total duration: ${totalDuration.toFixed(2)}s`)
  }

  // 如果流已完成且队列为空，准备结束
  if (audioStreamComplete && audioQueue.length === 0) {
    const remainingTime = Math.max(0, nextPlayTime - playbackContext.currentTime)
    console.log(`[Audio] Stream complete, waiting ${remainingTime.toFixed(2)}s to finish`)
    setTimeout(() => {
      finishStreamingPlayback()
    }, remainingTime * 1000 + 300)
  }
}

// 播放音频队列（PCM 16-bit 24kHz 格式）
const playNextAudio = async () => {
  if (isPlayingAudio || audioQueue.length === 0) return

  isPlayingAudio = true

  // 合并所有待播放的音频块
  const allBuffers: ArrayBuffer[] = []
  let totalLength = 0
  while (audioQueue.length > 0) {
    const buffer = audioQueue.shift()!
    allBuffers.push(buffer)
    totalLength += buffer.byteLength
  }

  if (allBuffers.length === 0 || totalLength === 0) {
    isPlayingAudio = false
    return
  }

  console.log(`[Audio] Playing ${allBuffers.length} chunks, total ${totalLength} bytes`)

  try {
    // 合并所有音频块
    const mergedBuffer = new Uint8Array(totalLength)
    let offset = 0
    for (const buffer of allBuffers) {
      mergedBuffer.set(new Uint8Array(buffer), offset)
      offset += buffer.byteLength
    }

    // Qwen-Omni 返回 PCM 16-bit 有符号整数，24kHz
    const int16Array = new Int16Array(mergedBuffer.buffer)
    const float32Array = new Float32Array(int16Array.length)

    // PCM 16-bit -> Float32 (-1.0 to 1.0)
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i]! / 32768.0
    }

    // 创建 AudioContext (24kHz 采样率)
    const playbackContext = new AudioContext({ sampleRate: 24000 })
    const audioBuffer = playbackContext.createBuffer(1, float32Array.length, 24000)
    audioBuffer.getChannelData(0).set(float32Array)

    console.log(`[Audio] PCM: samples=${float32Array.length}, duration=${(float32Array.length / 24000).toFixed(2)}s`)

    // 播放
    const source = playbackContext.createBufferSource()
    source.buffer = audioBuffer
    source.connect(playbackContext.destination)

    await new Promise<void>((resolve) => {
      source.onended = async () => {
        await playbackContext.close()
        resolve()
      }
      source.start()
    })
  } catch (e) {
    console.error('Play audio error:', e)
  }

  isPlayingAudio = false

  // 如果还有新的音频数据，继续播放
  if (audioQueue.length > 0) {
    playNextAudio()
    return
  }

  // 音频全部播放完成，检查是否需要切换到 listening
  if (pendingListeningStatus) {
    switchToListening()
  }
}

// 处理结束
const handleEnd = (reason: string) => {
  interviewStatus.value = 'stopped'
  stopAudioCapture()
  alert(`面试结束: ${reason}`)
}

// 处理错误
const handleError = (message: string) => {
  console.error('Server error:', message)
  connectionError.value = message
}

// 处理阶段变化
const handlePhaseChange = (message: any) => {
  currentPhase.value = message.phase
  phaseDescription.value = message.description || phaseNames[message.phase] || message.phase
  currentRound.value = message.round || 0
  maxRounds.value = message.max_rounds || 1

  // Add system message about phase change
  messages.value.push({
    id: Date.now().toString(),
    role: 'system',
    content: `--- ${phaseDescription.value} ---`,
    timestamp: new Date().toISOString()
  })
  scrollToBottom()
}

// 处理轮次更新（阶段内）
const handleRoundUpdate = (message: any) => {
  currentRound.value = message.round || 0
  maxRounds.value = message.max_rounds || 1
  console.log(`[Round] Updated: ${currentRound.value + 1}/${maxRounds.value} in ${message.phase}`)
}

// 处理面试结束
const handleInterviewEnd = (message: any) => {
  interviewStatus.value = 'stopped'
  if (message.evaluation) {
    const score = message.evaluation.overall_score
    const recommendation = message.evaluation.recommendation
    messages.value.push({
      id: Date.now().toString(),
      role: 'system',
      content: `面试结束！评分: ${score}/100, 推荐等级: ${recommendation}`,
      timestamp: new Date().toISOString()
    })

    // 3秒后跳转到完成页面
    setTimeout(() => {
      const token = route.params.token as string
      router.push({
        name: 'InterviewComplete',
        params: { token },
        query: {
          score: score.toString(),
          recommendation: recommendation
        }
      })
    }, 3000)
  }
  scrollToBottom()
}

// 启动音频采集
const startAudioCapture = async () => {
  if (!mediaStream || !audioContext) {
    console.error('No mediaStream or audioContext')
    return
  }

  console.log('Starting audio capture, sampleRate:', audioContext.sampleRate)

  // 直接使用 ScriptProcessor（更可靠）
  startAudioCaptureWithScriptProcessor()
}

// ScriptProcessorNode 音频采集
let scriptProcessor: ScriptProcessorNode | null = null

const startAudioCaptureWithScriptProcessor = () => {
  if (!mediaStream || !audioContext) {
    console.error('Cannot start audio capture: no mediaStream or audioContext')
    return
  }

  try {
    const source = audioContext.createMediaStreamSource(mediaStream)
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1)

    // 重采样参数
    let resampleBuffer: number[] = []
    const inputRate = audioContext.sampleRate
    const outputRate = 16000
    const ratio = inputRate / outputRate

    console.log(`Audio capture: inputRate=${inputRate}, outputRate=${outputRate}, ratio=${ratio}`)

    scriptProcessor.onaudioprocess = (e) => {
      // 只在 listening 状态才处理音频（分析中、面试官说话时都不采集）
      if (interviewStatus.value !== 'listening') {
        // 清空缓冲区，避免积累
        resampleBuffer = []
        volumeLevel.value = 0
        return
      }

      const input = e.inputBuffer.getChannelData(0)

      // 计算音量 (RMS)
      let sum = 0
      for (let i = 0; i < input.length; i++) {
        sum += (input[i] ?? 0) * (input[i] ?? 0)
      }
      const rms = Math.sqrt(sum / input.length)
      volumeLevel.value = Math.min(100, rms * 500) // 放大显示

      // 累积到重采样缓冲
      for (let i = 0; i < input.length; i++) {
        resampleBuffer.push(input[i] ?? 0)
      }

      // 检查 WebSocket 状态
      if (ws?.readyState !== WebSocket.OPEN) {
        return
      }

      // 每收集够一定量的数据就发送
      const outputSamples = Math.floor(resampleBuffer.length / ratio)
      if (outputSamples >= 320) { // 20ms @ 16kHz
        const output = new Int16Array(outputSamples)
        for (let i = 0; i < outputSamples; i++) {
          const idx = Math.floor(i * ratio)
          const sample = resampleBuffer[idx] || 0
          output[i] = Math.max(-32768, Math.min(32767, Math.floor(sample * 32767)))
        }

        // 发送音频数据
        try {
          const bytes = new Uint8Array(output.buffer)
          let binary = ''
          for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i] ?? 0)
          }
          const base64 = btoa(binary)

          ws.send(JSON.stringify({
            type: 'audio',
            audio: base64
          }))

          audioFrameCount.value++
        } catch (err) {
          console.error('Send audio error:', err)
        }

        // 清空已处理的缓冲
        resampleBuffer = resampleBuffer.slice(Math.floor(outputSamples * ratio))
      }
    }

    // 连接节点 - 注意：不要连接到 destination，避免回声
    source.connect(scriptProcessor)
    // 创建一个静音的目标节点来保持处理器活跃
    const silentGain = audioContext.createGain()
    silentGain.gain.value = 0
    scriptProcessor.connect(silentGain)
    silentGain.connect(audioContext.destination)

    console.log('Audio capture started successfully')
  } catch (err) {
    console.error('Failed to start audio capture:', err)
    connectionError.value = '音频采集启动失败'
  }
}

// 停止音频采集
const stopAudioCapture = () => {
  if (scriptProcessor) {
    scriptProcessor.disconnect()
    scriptProcessor = null
  }
  if (audioWorkletNode) {
    audioWorkletNode.disconnect()
    audioWorkletNode = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    mediaStream = null
  }
  volumeLevel.value = 0
  audioFrameCount.value = 0
}

// 手动提交音频（说完了）
const commitAudio = () => {
  if (ws?.readyState === WebSocket.OPEN && interviewStatus.value === 'listening') {
    console.log('Committing audio...')
    ws.send(JSON.stringify({
      type: 'commit'
    }))
    interviewStatus.value = 'processing'
  }
}

// 跳过当前面试官音频
const skipAudio = async () => {
  console.log('[Audio] Skipping audio playback')

  // 清空音频队列
  audioQueue.length = 0

  // 停止播放
  if (playbackContext && playbackContext.state !== 'closed') {
    try {
      await playbackContext.close()
    } catch (e) {
      console.error('Close playback context error:', e)
    }
  }
  playbackContext = null
  isStreamingPlayback = false
  audioStreamComplete = false
  nextPlayTime = 0

  // 完成当前响应文本消息
  if (currentResponse.value) {
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: currentResponse.value,
      timestamp: new Date().toISOString()
    })
    currentResponse.value = ''
    scrollToBottom()
  }

  // 切换到 listening 状态
  interviewStatus.value = 'listening'
  pendingListeningStatus = false
  startRecordingTimer()
}

// 结束面试
const endInterview = () => {
  if (!confirm('确定要结束面试吗？')) return

  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'stop'
    }))
  }

  interviewStatus.value = 'stopped'
  stopAudioCapture()
}

// 计时器
const startDurationTimer = () => {
  durationTimer = window.setInterval(() => {
    duration.value++
  }, 1000)
}

const startPingTimer = () => {
  pingTimer = window.setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000)
}

onMounted(() => {
  // 初始化
})

onUnmounted(() => {
  if (durationTimer) clearInterval(durationTimer)
  if (pingTimer) clearInterval(pingTimer)
  stopRecordingTimer()
  stopAudioCapture()
  if (ws) {
    ws.close()
    ws = null
  }
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
  // 清理播放 context
  if (playbackContext) {
    playbackContext.close()
    playbackContext = null
  }
  isStreamingPlayback = false
})
</script>

<style scoped>
/* 声波动画 */
.sound-wave {
  animation: soundWave 0.5s ease-in-out infinite alternate;
}

@keyframes soundWave {
  0% {
    height: 4px;
  }
  100% {
    height: 24px;
  }
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
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
