<template>
  <div class="h-screen bg-gray-50 flex">
    <!-- Left sidebar: Interview list -->
    <div class="w-80 bg-white border-r overflow-hidden flex flex-col">
      <div class="p-4 border-b">
        <h2 class="text-lg font-semibold">面试记录</h2>
        <!-- Filters -->
        <select v-model="statusFilter" class="mt-2 w-full border rounded p-2 text-sm">
          <option value="">全部状态</option>
          <option value="completed">已完成</option>
          <option value="voice">进行中</option>
          <option value="pending">待开始</option>
        </select>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索面试记录..."
          class="mt-2 w-full border rounded p-2 text-sm"
        />
      </div>
      <div class="flex-1 overflow-y-auto">
        <!-- Loading state -->
        <div v-if="loadingList" class="p-4 text-center text-gray-500">
          加载中...
        </div>
        <!-- Empty state -->
        <div v-else-if="filteredInterviews.length === 0" class="p-4 text-center text-gray-400">
          暂无面试记录
        </div>
        <!-- Interview items -->
        <div v-else v-for="interview in filteredInterviews" :key="interview.id"
          @click="selectInterview(interview.id)"
          class="p-4 border-b cursor-pointer hover:bg-gray-50 transition-colors"
          :class="{'bg-blue-50': selectedId === interview.id}">
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <span class="font-medium">{{ interview.id.slice(0, 8) }}...</span>
              <span class="text-xs ml-2 px-2 py-0.5 rounded-full"
                :class="statusClass(interview.status)">
                {{ statusText(interview.status) }}
              </span>
            </div>
            <span v-if="interview.evaluation?.overall_score" class="text-sm font-bold"
              :class="scoreClass(interview.evaluation.overall_score)">
              {{ interview.evaluation.overall_score }}分
            </span>
          </div>
          <div class="text-sm text-gray-500 mt-1">
            {{ formatDate(interview.created_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Main content: Replay interface -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <div v-if="!selectedId" class="flex-1 flex items-center justify-center text-gray-400">
        选择一个面试记录查看详情
      </div>

      <template v-else>
        <!-- Loading state for details -->
        <div v-if="loadingDetail" class="flex-1 flex items-center justify-center text-gray-500">
          加载中...
        </div>

        <template v-else-if="currentSession">
          <!-- Header with evaluation summary -->
          <div class="bg-white border-b p-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-xl font-semibold">面试回放</h3>
                <p class="text-sm text-gray-500 mt-1">
                  会话ID: {{ currentSession.id }}
                </p>
              </div>
              <div v-if="evaluation" class="flex items-center space-x-4">
                <div class="text-center">
                  <div class="text-3xl font-bold" :class="scoreClass(evaluation.overall_score)">
                    {{ evaluation.overall_score }}
                  </div>
                  <div class="text-xs text-gray-500">总分</div>
                </div>
                <div class="px-3 py-1 rounded-full text-sm font-medium"
                  :class="recommendationClass(evaluation.recommendation)">
                  {{ recommendationText(evaluation.recommendation) }}
                </div>
              </div>
            </div>

            <!-- Phase timeline -->
            <div v-if="phases.length > 0" class="mt-4 flex space-x-2">
              <button v-for="phase in phases" :key="phase.name"
                @click="jumpToPhase(phase.name)"
                class="px-3 py-1 text-sm rounded-full transition-colors"
                :class="phaseButtonClass(phase.name)">
                {{ phaseNames[phase.name] || phase.name }} ({{ phase.count }})
              </button>
            </div>
          </div>

          <!-- Dialogue list with audio -->
          <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <div v-if="dialogues.length === 0" class="text-center text-gray-400 py-8">
              暂无对话记录
            </div>
            <div v-else v-for="(dialogue, index) in dialogues" :key="dialogue.id"
              :ref="el => setDialogueRef(dialogue.phase, el)"
              class="bg-white rounded-lg p-4 shadow-sm transition-all"
              :class="{'ring-2 ring-yellow-400': dialogue.is_highlighted}">

              <div class="flex items-start justify-between">
                <div class="flex items-center space-x-2">
                  <span class="px-2 py-0.5 text-xs rounded-full"
                    :class="roleClass(dialogue.role)">
                    {{ roleText(dialogue.role) }}
                  </span>
                  <span class="text-xs text-gray-400">{{ phaseNames[dialogue.phase] || dialogue.phase }}</span>
                  <span class="text-xs text-gray-400">{{ formatTime(dialogue.timestamp) }}</span>
                </div>

                <button @click="toggleHighlight(dialogue)"
                  class="text-gray-400 hover:text-yellow-500 transition-colors"
                  :disabled="savingHighlight">
                  <svg class="w-5 h-5" :fill="dialogue.is_highlighted ? 'currentColor' : 'none'"
                    stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
                  </svg>
                </button>
              </div>

              <p class="mt-2 text-gray-800 whitespace-pre-wrap">{{ dialogue.content }}</p>

              <!-- Audio player -->
              <div v-if="dialogue.audio_url" class="mt-3">
                <audio :src="dialogue.audio_url" controls class="w-full h-8"></audio>
              </div>

              <!-- HR notes input -->
              <div v-if="dialogue.is_highlighted" class="mt-2">
                <textarea
                  v-model="dialogue.hr_notes"
                  @blur="saveHighlightNote(dialogue)"
                  placeholder="添加备注..."
                  class="w-full text-sm text-yellow-700 bg-yellow-50 p-2 rounded border border-yellow-200 focus:outline-none focus:ring-2 focus:ring-yellow-400"
                  rows="2"
                ></textarea>
              </div>
            </div>
          </div>

          <!-- Evaluation details panel -->
          <div v-if="evaluation" class="bg-white border-t p-4 max-h-64 overflow-y-auto">
            <h3 class="font-semibold mb-3">评估详情</h3>

            <!-- Dimension scores -->
            <div v-if="evaluation.dimensions && evaluation.dimensions.length > 0" class="grid grid-cols-5 gap-4 mb-4">
              <div v-for="dim in evaluation.dimensions" :key="dim.name" class="text-center">
                <div class="text-lg font-bold" :class="scoreClass(dim.score * 10)">
                  {{ dim.score }}
                </div>
                <div class="text-xs text-gray-500">{{ dim.name }}</div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <!-- Highlights -->
              <div v-if="evaluation.highlights && evaluation.highlights.length > 0">
                <h4 class="text-sm font-medium text-green-700 mb-2">亮点</h4>
                <ul class="text-sm text-gray-600 list-disc list-inside space-y-1">
                  <li v-for="(h, idx) in evaluation.highlights" :key="idx">{{ h }}</li>
                </ul>
              </div>

              <!-- Concerns -->
              <div v-if="evaluation.concerns && evaluation.concerns.length > 0">
                <h4 class="text-sm font-medium text-red-700 mb-2">顾虑</h4>
                <ul class="text-sm text-gray-600 list-disc list-inside space-y-1">
                  <li v-for="(c, idx) in evaluation.concerns" :key="idx">{{ c }}</li>
                </ul>
              </div>
            </div>

            <!-- Summary -->
            <div v-if="evaluation.summary" class="mt-4">
              <h4 class="text-sm font-medium text-gray-700 mb-2">总结</h4>
              <p class="text-sm text-gray-600">{{ evaluation.summary }}</p>
            </div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { request } from '../api/request'

// Types
interface InterviewSession {
  id: string
  token: string
  resume_id: string
  jd_id: string
  status: string
  written_test?: any
  voice_interview?: VoiceInterview
  evaluation?: Evaluation
  created_at: string
  started_at?: string
  completed_at?: string
}

interface VoiceInterview {
  started_at?: string
  ended_at?: string
  duration: number
  transcript: TranscriptMessage[]
  audio_url?: string
}

interface TranscriptMessage {
  role: string
  content: string
  audio_url?: string
  timestamp: string
  duration?: number
}

interface Evaluation {
  overall_score: number
  recommendation: string
  dimensions: DimensionScore[]
  highlights: string[]
  concerns: string[]
  summary: string
  detailed_analysis?: string
  generated_at?: string
}

interface DimensionScore {
  name: string
  score: number
  weight: float
  analysis?: string
}

interface Dialogue extends TranscriptMessage {
  id: string
  phase: string
  is_highlighted: boolean
  hr_notes?: string
}

interface Phase {
  name: string
  count: number
}

// State
const interviews = ref<InterviewSession[]>([])
const selectedId = ref<string>('')
const currentSession = ref<InterviewSession | null>(null)
const evaluation = ref<Evaluation | null>(null)
const dialogues = ref<Dialogue[]>([])
const phases = ref<Phase[]>([])
const dialogueRefs = ref<Map<string, any>>(new Map())

const statusFilter = ref<string>('')
const searchQuery = ref<string>('')
const loadingList = ref<boolean>(false)
const loadingDetail = ref<boolean>(false)
const savingHighlight = ref<boolean>(false)

const currentPhase = ref<string>('')

// Phase names mapping
const phaseNames: Record<string, string> = {
  'greeting': '开场问候',
  'background': '背景了解',
  'technical': '技术评估',
  'behavioral': '行为面试',
  'closing': '结束语',
  'opening': '开场',
  'experience': '经验交流',
  'skills': '技能评估',
  'questions': '问答环节',
  'farewell': '告别'
}

// Computed
const filteredInterviews = computed(() => {
  let result = interviews.value

  // Status filter
  if (statusFilter.value) {
    result = result.filter(i => i.status === statusFilter.value)
  }

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(i =>
      i.id.toLowerCase().includes(query) ||
      i.token.toLowerCase().includes(query)
    )
  }

  return result
})

// Methods
async function loadInterviews() {
  loadingList.value = true
  try {
    const response = await request.get('/interview/list', {
      params: { page: 1, size: 100 }
    })
    if (response.data) {
      interviews.value = response.data
    }
  } catch (error) {
    console.error('Failed to load interviews:', error)
  } finally {
    loadingList.value = false
  }
}

async function selectInterview(sessionId: string) {
  selectedId.value = sessionId
  loadingDetail.value = true

  try {
    // Load session details
    const sessionResponse = await request.get(`/interview/${sessionId}`)
    currentSession.value = sessionResponse.data

    // Load evaluation if available
    if (currentSession.value?.evaluation) {
      evaluation.value = currentSession.value.evaluation
    } else {
      try {
        const evalResponse = await request.get(`/interview/${sessionId}/evaluation`)
        evaluation.value = evalResponse.data
      } catch (err) {
        // Evaluation not available yet
        evaluation.value = null
      }
    }

    // Process dialogues from voice interview
    processDialogues()

  } catch (error) {
    console.error('Failed to load interview details:', error)
    currentSession.value = null
    evaluation.value = null
  } finally {
    loadingDetail.value = false
  }
}

function processDialogues() {
  if (!currentSession.value?.voice_interview?.transcript) {
    dialogues.value = []
    phases.value = []
    return
  }

  const transcript = currentSession.value.voice_interview.transcript
  const processedDialogues: Dialogue[] = []
  const phaseCount: Record<string, number> = {}

  transcript.forEach((msg, index) => {
    // Determine phase based on index (simplified logic)
    let phase = 'general'
    if (index < 2) phase = 'greeting'
    else if (index < transcript.length / 3) phase = 'background'
    else if (index < transcript.length * 2 / 3) phase = 'technical'
    else phase = 'closing'

    phaseCount[phase] = (phaseCount[phase] || 0) + 1

    processedDialogues.push({
      id: `${currentSession.value!.id}-${index}`,
      role: msg.role,
      content: msg.content,
      audio_url: msg.audio_url,
      timestamp: msg.timestamp,
      duration: msg.duration,
      phase,
      is_highlighted: false,
      hr_notes: ''
    })
  })

  dialogues.value = processedDialogues

  // Build phases list
  phases.value = Object.entries(phaseCount).map(([name, count]) => ({
    name,
    count
  }))
}

async function toggleHighlight(dialogue: Dialogue) {
  if (savingHighlight.value) return

  dialogue.is_highlighted = !dialogue.is_highlighted

  // Save to backend (if API exists)
  savingHighlight.value = true
  try {
    await request.post(`/interview/${currentSession.value!.id}/highlight`, {
      dialogue_id: dialogue.id,
      is_highlighted: dialogue.is_highlighted,
      notes: dialogue.hr_notes || ''
    })
  } catch (error) {
    console.error('Failed to save highlight:', error)
    // Revert on error
    dialogue.is_highlighted = !dialogue.is_highlighted
  } finally {
    savingHighlight.value = false
  }
}

async function saveHighlightNote(dialogue: Dialogue) {
  if (!dialogue.is_highlighted) return

  try {
    await request.post(`/interview/${currentSession.value!.id}/highlight`, {
      dialogue_id: dialogue.id,
      is_highlighted: true,
      notes: dialogue.hr_notes || ''
    })
  } catch (error) {
    console.error('Failed to save note:', error)
  }
}

function jumpToPhase(phaseName: string) {
  const element = dialogueRefs.value.get(phaseName)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    currentPhase.value = phaseName
  }
}

function setDialogueRef(phase: string, el: any) {
  if (el && !dialogueRefs.value.has(phase)) {
    dialogueRefs.value.set(phase, el)
  }
}

function phaseButtonClass(phaseName: string): string {
  return currentPhase.value === phaseName
    ? 'bg-blue-500 text-white'
    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
}

// Helper functions
function statusClass(status: string): string {
  const classes: Record<string, string> = {
    'pending': 'bg-gray-100 text-gray-700',
    'written_test': 'bg-blue-100 text-blue-700',
    'voice': 'bg-yellow-100 text-yellow-700',
    'completed': 'bg-green-100 text-green-700',
    'cancelled': 'bg-red-100 text-red-700'
  }
  return classes[status] || classes.pending
}

function statusText(status: string): string {
  const texts: Record<string, string> = {
    'pending': '待开始',
    'written_test': '笔试中',
    'voice': '面试中',
    'completed': '已完成',
    'cancelled': '已取消'
  }
  return texts[status] || status
}

function scoreClass(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function recommendationClass(recommendation: string): string {
  const classes: Record<string, string> = {
    'strongly_recommend': 'bg-green-500 text-white',
    'recommend': 'bg-green-100 text-green-700',
    'neutral': 'bg-yellow-100 text-yellow-700',
    'not_recommend': 'bg-red-100 text-red-700'
  }
  return classes[recommendation] || classes.neutral
}

function recommendationText(recommendation: string): string {
  const texts: Record<string, string> = {
    'strongly_recommend': '强烈推荐',
    'recommend': '推荐',
    'neutral': '中立',
    'not_recommend': '不推荐'
  }
  return texts[recommendation] || recommendation
}

function roleClass(role: string): string {
  return role === 'interviewer' || role === 'assistant'
    ? 'bg-blue-100 text-blue-700'
    : 'bg-green-100 text-green-700'
}

function roleText(role: string): string {
  if (role === 'interviewer' || role === 'assistant') return '面试官'
  if (role === 'candidate' || role === 'user') return '候选人'
  return role
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`

  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatTime(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// Lifecycle
onMounted(() => {
  loadInterviews()
})
</script>

<style scoped>
/* Custom scrollbar */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
