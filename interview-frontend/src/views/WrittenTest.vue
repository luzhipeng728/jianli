<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部固定进度条 -->
    <div v-if="isGenerating" class="fixed top-0 left-0 right-0 z-50">
      <!-- 进度条背景 -->
      <div class="h-2 bg-gray-200">
        <div
          class="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500 transition-all duration-300 ease-out progress-bar-shimmer"
          :style="{ width: `${(completedCount / totalQuestions) * 100}%` }"
        ></div>
      </div>
      <!-- 进度信息条 -->
      <div class="bg-white/95 backdrop-blur-sm border-b border-gray-200 px-4 py-2 shadow-sm">
        <div class="max-w-4xl mx-auto flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="relative">
              <svg class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            </div>
            <span class="text-sm font-medium text-gray-700">{{ streamingStatus }}</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-500">进度</span>
            <span class="text-lg font-bold text-blue-600">{{ completedCount }}/{{ totalQuestions }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="py-8 px-4" :class="{ 'pt-20': isGenerating || isEvaluating || evaluationComplete }">
      <div class="max-w-4xl mx-auto">
        <!-- 顶部信息栏 -->
        <div class="card p-4 mb-6 flex justify-between items-center sticky top-0 z-40 bg-white/95 backdrop-blur-sm" :class="{ 'top-16': isGenerating || isEvaluating || evaluationComplete }">
          <div>
            <h1 class="text-xl font-bold text-gray-900">笔试测评</h1>
            <p class="text-sm text-gray-600">
              {{ isGenerating ? `正在生成题目 (${completedCount}/${totalQuestions})` : `共 ${questions.length} 题` }}
            </p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold" :class="isGenerating ? 'text-gray-400' : 'text-primary-600'">
              {{ isGenerating ? '--:--' : formatTime(timeRemaining) }}
            </div>
            <p class="text-sm text-gray-600">{{ isGenerating ? '生成完成后开始计时' : '剩余时间' }}</p>
          </div>
        </div>

        <!-- 生成状态提示 -->
        <div v-if="isGenerating" class="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mb-6 flex items-center">
          <div class="relative mr-3 flex-shrink-0">
            <div class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
              </svg>
            </div>
            <div class="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white animate-pulse"></div>
          </div>
          <div class="flex-1">
            <p class="text-blue-800 font-medium">AI 正在为您定制专属题目</p>
            <p class="text-blue-600 text-sm">请稍候，生成完成后即可开始作答...</p>
          </div>
        </div>

        <!-- 错误提示 -->
        <div v-if="error" class="card p-8 text-center mb-6">
          <div class="text-red-500 text-5xl mb-4">⚠</div>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">题目生成失败</h2>
          <p class="text-gray-600 mb-4">{{ error }}</p>
          <button @click="loadQuestions" class="btn btn-primary">重试</button>
        </div>

        <!-- 题目列表 - 流式渲染 -->
        <div class="space-y-6">
        <div
          v-for="(question, index) in questions"
          :key="index"
          :ref="(el) => setQuestionRef(question.id, el as HTMLElement)"
          class="card p-6 question-card"
        >
          <div class="flex items-start mb-4">
            <span class="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center font-semibold mr-3">
              {{ index + 1 }}
            </span>
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="px-2 py-0.5 text-xs rounded-full"
                  :class="{
                    'bg-blue-100 text-blue-700': question.type === 'single',
                    'bg-purple-100 text-purple-700': question.type === 'multiple',
                    'bg-orange-100 text-orange-700': question.type === 'judgment'
                  }"
                >
                  {{ getQuestionTypeLabel(question.type) }}
                </span>
                <span v-if="question.points" class="text-sm text-gray-500">{{ question.points }} 分</span>
              </div>
              <!-- 题目内容 - 流式显示 -->
              <p class="text-lg font-medium text-gray-900">
                {{ question.content }}
                <span v-if="question.isStreaming && currentField === 'CONTENT'" class="inline-block w-2 h-5 bg-primary-500 animate-pulse ml-1"></span>
              </p>
            </div>
          </div>

          <!-- 选项 - 流式显示 -->
          <div class="ml-11 space-y-2">
            <div
              v-for="(option, optIndex) in question.options"
              :key="optIndex"
              class="option-item"
            >
              <label
                class="flex items-center p-3 border rounded-lg transition-colors"
                :class="[
                  question.isComplete && !isGenerating ? 'cursor-pointer hover:bg-gray-50' : 'cursor-not-allowed opacity-75',
                  { 'border-primary-500 bg-primary-50': getAnswer(question.id) === option || (Array.isArray(getAnswer(question.id)) && (getAnswer(question.id) as string[]).includes(option)) }
                ]"
              >
                <input
                  v-if="question.type === 'multiple'"
                  type="checkbox"
                  :value="option"
                  :checked="(answers[question.id] as string[] || []).includes(option)"
                  @change="toggleMultipleAnswer(question.id, option)"
                  class="mr-3"
                  :disabled="!question.isComplete || isGenerating"
                />
                <input
                  v-else
                  type="radio"
                  :name="`question-${question.id}`"
                  :value="option"
                  v-model="answers[question.id]"
                  class="mr-3"
                  :disabled="!question.isComplete || isGenerating"
                />
                <span>
                  {{ option }}
                  <span v-if="question.isStreaming && currentField === `OPTION_${String.fromCharCode(65 + optIndex)}`" class="inline-block w-2 h-4 bg-primary-500 animate-pulse ml-1"></span>
                </span>
              </label>
            </div>

            <!-- 正在生成的选项占位 -->
            <div
              v-if="question.isStreaming && question.options.length < getExpectedOptionCount(question.type)"
              class="flex items-center p-3 border border-dashed border-gray-300 rounded-lg bg-gray-50"
            >
              <div class="w-4 h-4 bg-gray-200 rounded mr-3 animate-pulse"></div>
              <div class="flex-1 h-4 bg-gray-200 rounded animate-pulse"></div>
            </div>

            <!-- 评估结果内联显示 -->
            <div v-if="getQuestionResult(question.id)" class="mt-4 pt-4 border-t border-gray-200">
              <div class="flex items-center mb-2">
                <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mr-2"
                  :class="getQuestionResult(question.id)?.is_correct ? 'bg-green-500' : 'bg-red-500'">
                  <svg v-if="getQuestionResult(question.id)?.is_correct" class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                  </svg>
                  <svg v-else class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </div>
                <span class="font-medium" :class="getQuestionResult(question.id)?.is_correct ? 'text-green-700' : 'text-red-700'">
                  {{ getQuestionResult(question.id)?.is_correct ? '回答正确' : '回答错误' }}
                </span>
                <span class="ml-2 text-sm" :class="getQuestionResult(question.id)?.is_correct ? 'text-green-600' : 'text-red-600'">
                  {{ getQuestionResult(question.id)?.is_correct ? `+${getQuestionResult(question.id)?.points}分` : '0分' }}
                </span>
              </div>
              <!-- 错题AI解析 (Markdown格式) -->
              <div v-if="!getQuestionResult(question.id)?.is_correct && getQuestionResult(question.id)?.evaluation"
                class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center mb-2">
                  <svg class="w-5 h-5 text-red-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                  </svg>
                  <span class="font-medium text-red-700">AI 解析</span>
                  <span v-if="getQuestionResult(question.id)?.isEvaluating" class="ml-2 inline-block w-2 h-4 bg-red-500 animate-pulse"></span>
                </div>
                <div class="text-red-800 prose prose-sm max-w-none prose-headings:text-red-900 prose-p:text-red-800 prose-strong:text-red-900" v-html="renderMarkdown(getQuestionResult(question.id)?.evaluation || '')"></div>
              </div>
              <!-- 正在生成AI解析的占位 -->
              <div v-else-if="!getQuestionResult(question.id)?.is_correct && getQuestionResult(question.id)?.isEvaluating"
                class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center">
                  <svg class="w-5 h-5 text-red-600 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  <span class="text-red-700">AI 正在分析此题...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 正在生成新题目的卡片 -->
        <div v-if="isGenerating && questions.length < totalQuestions && !questions.some(q => q.isStreaming)" class="card p-6 border-dashed border-2 border-gray-300 bg-gray-50">
          <div class="flex items-center">
            <div class="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center mr-3 animate-pulse">
              {{ questions.length + 1 }}
            </div>
            <div class="flex-1 space-y-2">
              <div class="h-4 bg-gray-200 rounded w-1/4 animate-pulse"></div>
              <div class="h-5 bg-gray-200 rounded w-3/4 animate-pulse"></div>
            </div>
          </div>
        </div>

        <!-- 提交按钮 -->
        <div v-if="questions.length > 0 && !isEvaluating && !evaluationComplete" class="card p-6">
          <div class="flex justify-between items-center">
            <p class="text-gray-600">
              已完成 {{ answeredCount }} / {{ completedCount }} 题
            </p>
            <button
              @click="submitTest"
              class="btn btn-primary"
              :disabled="submitting || isGenerating"
            >
              {{ isGenerating ? '请等待题目生成完成' : (submitting ? '提交中...' : '提交答卷') }}
            </button>
          </div>
        </div>

        <!-- 评估进度条（固定在顶部） -->
        <div v-if="isEvaluating || evaluationComplete" class="fixed top-0 left-0 right-0 z-50">
          <div class="h-2 bg-gray-200">
            <div
              class="h-full bg-gradient-to-r from-green-500 via-blue-500 to-purple-500 transition-all duration-300 progress-bar-shimmer"
              :style="{ width: `${evaluationProgress}%` }"
            ></div>
          </div>
          <div class="bg-white/95 backdrop-blur-sm border-b border-gray-200 px-4 py-2 shadow-sm">
            <div class="max-w-4xl mx-auto flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <div class="relative">
                  <svg v-if="!evaluationComplete" class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  <svg v-else class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                  </svg>
                </div>
                <span class="text-sm font-medium text-gray-700">{{ evaluationStatus }}</span>
              </div>
              <div class="flex items-center space-x-4">
                <span class="text-sm text-gray-500">{{ evaluationProgress }}%</span>
                <span v-if="evaluationComplete" class="text-lg font-bold" :class="finalScore >= 60 ? 'text-green-600' : 'text-red-600'">
                  {{ finalScore.toFixed(0) }}分
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 最终得分和进入面试按钮 -->
        <div v-if="evaluationComplete" class="card p-6">
          <div class="text-center py-4">
            <div class="text-5xl font-bold mb-2" :class="finalScore >= 60 ? 'text-green-600' : 'text-red-600'">
              {{ finalScore.toFixed(0) }}分
            </div>
            <p class="text-gray-600 mb-4">
              共 {{ totalQuestions }} 题，答对 {{ correctCount }} 题
            </p>
            <button
              @click="goToVoiceInterview"
              class="btn btn-primary px-8"
            >
              进入语音面试
            </button>
          </div>
        </div>
        </div>
      </div>

      <!-- 无题目时的加载状态 -->
      <div v-if="questions.length === 0 && isGenerating && !error" class="card p-12 text-center">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
          <svg class="w-8 h-8 text-primary-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900 mb-2">正在初始化笔试</h2>
        <p class="text-gray-600">AI 正在为您准备专属题目，第一道题即将出现...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { interviewApi } from '../api/interview'

interface StreamingQuestion {
  id: string
  type: string
  content: string
  options: string[]
  points: number
  correct_answer: string | string[]
  isStreaming: boolean
  isComplete: boolean
}

const route = useRoute()
const router = useRouter()

const isGenerating = ref(true)
const streamingStatus = ref('正在连接服务器...')
const currentField = ref('')
const totalQuestions = ref(5)
const completedCount = ref(0)
const error = ref('')
const submitting = ref(false)
const questions = ref<StreamingQuestion[]>([])
const answers = ref<Record<string, string | string[]>>({})
const timeRemaining = ref(30 * 60)
let timer: number | null = null

// 评估相关状态
const isEvaluating = ref(false)
const evaluationComplete = ref(false)
const evaluationStatus = ref('准备评估...')
const evaluationProgress = ref(0)
const questionResults = ref<Array<{
  index: number
  question_id: string
  is_correct: boolean
  points: number
  evaluation?: string
  isEvaluating?: boolean
}>>([])
const finalScore = ref(0)
const correctCount = ref(0)

// 题目DOM引用，用于滚动定位
const questionRefs = ref<Map<string, HTMLElement>>(new Map())

// 设置题目DOM引用
const setQuestionRef = (questionId: string, el: HTMLElement | null) => {
  if (el) {
    questionRefs.value.set(questionId, el)
  }
}

// 获取题目评估结果
const getQuestionResult = (questionId: string) => {
  return questionResults.value.find(r => r.question_id === questionId)
}

// 滚动到指定题目（显示在视口顶部）
const scrollToQuestion = (questionId: string) => {
  const el = questionRefs.value.get(questionId)
  if (el) {
    const headerOffset = isGenerating.value ? 120 : 80 // 考虑固定头部高度
    const elementPosition = el.getBoundingClientRect().top + window.scrollY
    const offsetPosition = elementPosition - headerOffset

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    })
  }
}

// 简单的Markdown渲染（支持基本格式）
const renderMarkdown = (text: string): string => {
  if (!text) return ''

  return text
    // 转义HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 粗体 **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 斜体 *text*
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 代码 `code`
    .replace(/`(.+?)`/g, '<code class="bg-red-100 px-1 rounded text-red-900">$1</code>')
    // 换行
    .replace(/\n/g, '<br>')
    // 列表项 - item
    .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
    // 数字列表 1. item
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>')
}

const token = computed(() => route.params.token as string)

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  window.scrollTo({
    top: document.documentElement.scrollHeight,
    behavior: 'smooth'
  })
}

const answeredCount = computed(() => {
  return Object.values(answers.value).filter(answer => {
    if (Array.isArray(answer)) return answer.length > 0
    return answer && String(answer).trim() !== ''
  }).length
})

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const getQuestionTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    'single': '单选题',
    'multiple': '多选题',
    'judgment': '判断题'
  }
  return labels[type] || type
}

const getExpectedOptionCount = (type: string) => {
  return type === 'judgment' ? 2 : 4
}

const getAnswer = (questionId: string) => {
  return answers.value[questionId]
}

const toggleMultipleAnswer = (questionId: string, option: string) => {
  if (!answers.value[questionId]) {
    answers.value[questionId] = []
  }
  const arr = answers.value[questionId] as string[]
  const idx = arr.indexOf(option)
  if (idx > -1) {
    arr.splice(idx, 1)
  } else {
    arr.push(option)
  }
}

const loadQuestions = async () => {
  isGenerating.value = true
  error.value = ''
  questions.value = []
  completedCount.value = 0
  streamingStatus.value = '正在连接服务器...'

  const streamUrl = interviewApi.getWrittenQuestionsStreamUrl(token.value)
  const eventSource = new EventSource(streamUrl)

  let currentQuestionIndex = -1

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'start':
          totalQuestions.value = data.total
          streamingStatus.value = `开始生成 ${data.total} 道题目...`
          break

        case 'question_start':
          currentQuestionIndex = data.index - 1
          // 创建新的题目卡片
          questions.value.push({
            id: `q-${data.index}`,
            type: data.question_type,
            content: '',
            options: [],
            points: 10,
            correct_answer: '',
            isStreaming: true,
            isComplete: false
          })
          // 初始化答案
          if (data.question_type === 'multiple') {
            answers.value[`q-${data.index}`] = []
          } else {
            answers.value[`q-${data.index}`] = ''
          }
          streamingStatus.value = `正在生成第 ${data.index} 题 (${getQuestionTypeLabel(data.question_type)})...`
          // 新题目出现时滚动到底部
          scrollToBottom()
          break

        case 'field_start':
          currentField.value = data.field
          break

        case 'chunk':
          // 流式更新当前题目的内容
          if (currentQuestionIndex >= 0 && currentQuestionIndex < questions.value.length) {
            const q = questions.value[currentQuestionIndex]!
            const field = data.field
            // 清理数据中的结束标签
            let value = data.value || ''
            value = value.replace(/\[\/[A-Z_]+\]/g, '').replace(/^\n+|\n+$/g, '')

            if (field === 'CONTENT') {
              q.content += value
            } else if (field === 'POINTS') {
              try {
                q.points = parseInt(value) || 10
              } catch {
                // ignore
              }
            } else if (field?.startsWith('OPTION_')) {
              const optionLetter = field.split('_')[1]
              const optionIndex = optionLetter.charCodeAt(0) - 65 // A=0, B=1, etc.

              // 确保选项数组足够长
              while (q.options.length <= optionIndex) {
                q.options.push('')
              }

              // 追加内容到对应选项（带字母前缀）
              if (q.options[optionIndex] === '') {
                q.options[optionIndex] = `${optionLetter}. ${value}`
              } else {
                q.options[optionIndex] += value
              }
              // 选项增加时滚动到底部
              scrollToBottom()
            }
          }
          break

        case 'complete':
          // 单道题目生成完成
          if (currentQuestionIndex >= 0 && currentQuestionIndex < questions.value.length) {
            const q = questions.value[currentQuestionIndex]!
            q.isStreaming = false
            q.isComplete = true

            // 更新完整数据（如果后端返回了）
            if (data.data) {
              q.id = data.data.id || q.id
              // 只在内容为空时使用后端数据
              if (!q.content && data.data.content) {
                q.content = data.data.content
              }
              // 处理选项 - 添加字母前缀
              if (data.data.options && data.data.options.length > 0) {
                q.options = data.data.options.map((opt: string, idx: number) => {
                  const letter = String.fromCharCode(65 + idx)
                  if (!opt.startsWith(letter + '.') && !opt.startsWith(letter + ' ')) {
                    return `${letter}. ${opt}`
                  }
                  return opt
                })
              }
              q.points = data.data.points || q.points || 10
              q.correct_answer = data.data.correct_answer || ''

              // 更新答案key
              const oldKey = `q-${currentQuestionIndex + 1}`
              if (answers.value[oldKey] !== undefined && data.data.id) {
                answers.value[data.data.id] = answers.value[oldKey]
                if (oldKey !== data.data.id) {
                  delete answers.value[oldKey]
                }
              }
            }

            // 清理选项中可能残留的标签
            q.options = q.options.map(opt => opt.replace(/\[\/[A-Z_]+\]/g, '').trim())

            completedCount.value = currentQuestionIndex + 1
            currentField.value = ''
          }
          break

        case 'error':
          console.error('Generation error:', data.message)
          streamingStatus.value = `第 ${data.index} 题生成出错，继续下一题...`
          break

        case 'all_complete':
          eventSource.close()
          isGenerating.value = false
          streamingStatus.value = '全部题目生成完成！'
          startTimer()
          break
      }
    } catch (e) {
      console.error('Failed to parse SSE data:', e)
    }
  }

  eventSource.onerror = (e) => {
    console.error('SSE connection error:', e)
    eventSource.close()

    if (questions.value.length === 0) {
      error.value = '连接服务器失败，请重试'
      isGenerating.value = false
    } else {
      // 有部分题目，允许作答
      isGenerating.value = false
      startTimer()
    }
  }
}

const submitTest = async () => {
  const completeQuestions = questions.value.filter(q => q.isComplete)
  if (answeredCount.value < completeQuestions.length) {
    if (!confirm('还有题目未完成,确定要提交吗?')) {
      return
    }
  }

  // 停止计时器
  if (timer) {
    clearInterval(timer)
    timer = null
  }

  try {
    submitting.value = true
    isEvaluating.value = true
    evaluationStatus.value = '正在提交答案...'

    // 构建提交数据，包含题目信息以便后端评分
    const submitData = {
      sessionId: token.value,
      answers: Object.entries(answers.value).map(([questionId, answer]) => ({
        questionId,
        answer
      })),
      // 包含完整题目信息（含正确答案）供后端评分
      questions: completeQuestions.map(q => ({
        id: q.id,
        type: q.type,
        content: q.content,
        options: q.options,
        correctAnswer: q.correct_answer,  // 使用正确的字段名
        points: q.points || 10
      })),
      submittedAt: new Date().toISOString()
    }

    // 使用 fetch API 发送 POST 请求并处理 SSE 流
    const response = await fetch(interviewApi.getWrittenSubmitStreamUrl(token.value), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(submitData)
    })

    if (!response.ok) {
      throw new Error('提交失败')
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('无法读取响应流')
    }

    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handleEvaluationEvent(data)
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }

  } catch (err: any) {
    alert('提交失败: ' + err.message)
    isEvaluating.value = false
  } finally {
    submitting.value = false
  }
}

const handleEvaluationEvent = (data: any) => {
  switch (data.type) {
    case 'start':
      totalQuestions.value = data.total
      evaluationStatus.value = `开始评估 ${data.total} 道题目...`
      evaluationProgress.value = 5
      break

    case 'checking':
      evaluationStatus.value = `正在检查第 ${data.index}/${data.total} 题...`
      // 进度 = 5% + (当前题号 / 总题数) * 90%
      evaluationProgress.value = 5 + ((data.index - 1) / data.total) * 90
      // 滚动到正在检查的题目
      if (data.question_id) {
        scrollToQuestion(data.question_id)
      }
      break

    case 'question_result':
      questionResults.value.push({
        index: data.index,
        question_id: data.question_id || questions.value[data.index - 1]?.id || '',
        is_correct: data.is_correct,
        points: data.points,
        evaluation: '',
        isEvaluating: false
      })
      // 更新进度
      evaluationProgress.value = 5 + (data.index / totalQuestions.value) * 90
      // 更新状态
      if (data.is_correct) {
        evaluationStatus.value = `第 ${data.index} 题 ✓ 正确`
      } else {
        evaluationStatus.value = `第 ${data.index} 题 ✗ 错误，AI正在分析...`
      }
      // 滚动到该题目位置
      nextTick(() => {
        const questionId = data.question_id || questions.value[data.index - 1]?.id
        if (questionId) {
          scrollToQuestion(questionId)
        }
      })
      break

    case 'evaluating':
      // 根据question_id或index找到对应结果
      const resultItem = data.question_id
        ? questionResults.value.find(r => r.question_id === data.question_id)
        : questionResults.value.find(r => r.index === data.index)
      if (resultItem) {
        resultItem.isEvaluating = true
      }
      evaluationStatus.value = `第 ${data.index} 题 AI分析中...`
      break

    case 'evaluation_chunk':
      const chunkResult = data.question_id
        ? questionResults.value.find(r => r.question_id === data.question_id)
        : questionResults.value.find(r => r.index === data.index)
      if (chunkResult) {
        chunkResult.evaluation = (chunkResult.evaluation || '') + data.chunk
      }
      break

    case 'evaluation_done':
      const doneResult = data.question_id
        ? questionResults.value.find(r => r.question_id === data.question_id)
        : questionResults.value.find(r => r.index === data.index)
      if (doneResult) {
        doneResult.isEvaluating = false
        doneResult.evaluation = data.evaluation
      }
      evaluationStatus.value = `第 ${data.index} 题分析完成`
      break

    case 'all_complete':
      evaluationStatus.value = '评估完成！'
      evaluationProgress.value = 100
      evaluationComplete.value = true
      isEvaluating.value = false
      finalScore.value = data.score
      correctCount.value = data.correct_count
      break

    case 'evaluation_error':
      console.error('评估错误:', data.error)
      const errorResult = data.question_id
        ? questionResults.value.find(r => r.question_id === data.question_id)
        : questionResults.value.find(r => r.index === data.index)
      if (errorResult) {
        errorResult.isEvaluating = false
        errorResult.evaluation = '分析失败，请稍后重试'
      }
      break
  }
}

const goToVoiceInterview = () => {
  router.push(`/${token.value}/voice`)
}

const startTimer = () => {
  timer = window.setInterval(() => {
    timeRemaining.value--
    if (timeRemaining.value <= 0) {
      clearInterval(timer!)
      alert('时间到,自动提交!')
      submitTest()
    }
  }, 1000)
}

onMounted(() => {
  loadQuestions()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
/* 进度条闪光动画 */
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.progress-bar-shimmer {
  background-image: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.4) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: shimmer 2s ease-in-out infinite;
}

/* 题目卡片滑入动画 */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.question-card {
  animation: slideUp 0.4s ease-out forwards;
}

.option-item {
  animation: slideUp 0.3s ease-out forwards;
}

/* 减少动画偏好支持 */
@media (prefers-reduced-motion: reduce) {
  .progress-bar-shimmer {
    animation: none;
  }
  .question-card,
  .option-item {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
</style>
