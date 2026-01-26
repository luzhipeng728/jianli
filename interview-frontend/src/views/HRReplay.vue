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
        <div v-else v-for="interview in filteredInterviews" :key="interview.session_id"
          @click="selectInterview(interview.session_id)"
          class="p-4 border-b cursor-pointer hover:bg-gray-50 transition-colors group"
          :class="{'bg-blue-50': selectedId === interview.session_id}">
          <div class="flex justify-between items-start">
            <div class="flex-1 min-w-0">
              <span class="font-medium">{{ interview.session_id.slice(0, 16) }}...</span>
              <span class="text-xs ml-2 px-2 py-0.5 rounded-full"
                :class="statusClass(interview.status)">
                {{ statusText(interview.status) }}
              </span>
            </div>
            <div class="flex items-center space-x-2">
              <span v-if="interview.evaluation_score" class="text-sm font-bold"
                :class="scoreClass(interview.evaluation_score)">
                {{ interview.evaluation_score }}分
              </span>
              <!-- 删除按钮 -->
              <button
                @click.stop="deleteInterview(interview.session_id)"
                class="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                title="删除此记录"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
              </button>
            </div>
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

        <template v-else-if="currentRecord">
          <!-- Header with evaluation summary -->
          <div class="bg-white border-b p-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-xl font-semibold">面试回放</h3>
                <p class="text-sm text-gray-500 mt-1">
                  会话ID: {{ currentRecord.session_id }}
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
            <div v-else v-for="dialogue in dialogues" :key="dialogue.id"
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

          <!-- Written Test Results Panel -->
          <div v-if="writtenTest" class="bg-white border-t">
            <button
              @click="showWrittenTest = !showWrittenTest"
              class="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div class="flex items-center space-x-3">
                <h3 class="font-semibold">笔试成绩</h3>
                <span class="px-2 py-0.5 text-sm rounded-full" :class="scoreClass(writtenTest.score)">
                  {{ writtenTest.score.toFixed(1) }}分
                </span>
                <span class="text-sm text-gray-500">
                  ({{ writtenTest.correct_count }}/{{ writtenTest.total_questions }} 正确)
                </span>
              </div>
              <svg
                class="w-5 h-5 text-gray-400 transition-transform"
                :class="{ 'rotate-180': showWrittenTest }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <div v-show="showWrittenTest" class="px-4 pb-4 max-h-80 overflow-y-auto">
              <div class="space-y-4">
                <div
                  v-for="(question, index) in writtenTest.questions"
                  :key="question.id"
                  class="p-3 rounded-lg border"
                  :class="getAnswerStatus(question.id) ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex-1">
                      <div class="flex items-center space-x-2 mb-2">
                        <span class="text-sm font-medium text-gray-500">Q{{ index + 1 }}</span>
                        <span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                          {{ getQuestionTypeText(question.type) }}
                        </span>
                        <span class="text-xs text-gray-400">{{ question.points }}分</span>
                      </div>
                      <p class="text-sm text-gray-800 mb-2">{{ question.content }}</p>

                      <!-- Options for choice questions -->
                      <div v-if="question.options && question.options.length > 0" class="ml-2 space-y-1">
                        <div
                          v-for="(option, optIdx) in question.options"
                          :key="optIdx"
                          class="text-sm flex items-center space-x-2"
                          :class="getOptionClass(question, option)"
                        >
                          <span>{{ String.fromCharCode(65 + optIdx) }}.</span>
                          <span>{{ option }}</span>
                          <span v-if="isCorrectOption(question, option)" class="text-green-600 text-xs">(正确答案)</span>
                          <span v-if="isUserAnswer(question.id, option) && !isCorrectOption(question, option)" class="text-red-600 text-xs">(用户选择)</span>
                        </div>
                      </div>

                      <!-- User answer display for non-choice questions -->
                      <div v-else class="mt-2 text-sm">
                        <div class="text-gray-600">
                          <span class="font-medium">用户答案：</span>
                          {{ getUserAnswer(question.id) }}
                        </div>
                        <div class="text-green-700">
                          <span class="font-medium">正确答案：</span>
                          {{ formatCorrectAnswer(question.correct_answer) }}
                        </div>
                      </div>

                      <!-- AI 解析（仅错题显示） -->
                      <div v-if="!getAnswerStatus(question.id) && getAIEvaluation(question.id)"
                        class="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <div class="flex items-start space-x-2">
                          <svg class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                          </svg>
                          <div>
                            <span class="text-xs font-medium text-blue-700">AI 解析</span>
                            <p class="text-sm text-blue-800 mt-1">{{ getAIEvaluation(question.id) }}</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="ml-3">
                      <svg v-if="getAnswerStatus(question.id)" class="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                      </svg>
                      <svg v-else class="w-6 h-6 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                      </svg>
                    </div>
                  </div>
                </div>
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
import { useRoute } from 'vue-router'
import { request } from '../api/request'

// Types - Using structured interview record format
interface InterviewRecord {
  session_id: string
  resume_id: string
  jd_id: string
  status: string
  current_phase: string
  current_round: number
  dialogues: DialogueEntry[]
  phase_transitions: PhaseTransition[]
  created_at: string
  started_at?: string
  completed_at?: string
  evaluation?: Evaluation
  hr_watchers: string[]
  hr_interventions: any[]
  audio_dir?: string
}

interface DialogueEntry {
  id: string
  role: string
  content: string
  phase: string
  round_number: number
  audio_path?: string
  audio_url?: string
  duration_seconds?: number
  timestamp: string
  is_highlighted: boolean
  hr_notes?: string
}

interface PhaseTransition {
  from_phase: string
  to_phase: string
  reason: string
  timestamp: string
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
  weight: number
  feedback?: string
}

interface WrittenTestQuestion {
  id: string
  type: string
  content: string
  options: string[]
  correct_answer: string | string[]
  points: number
}

interface WrittenTestAnswer {
  question_id: string
  answer: string | string[]
  is_correct: boolean
  ai_evaluation?: string  // AI解析
}

interface WrittenTest {
  score: number
  total_questions: number
  correct_count: number
  questions: WrittenTestQuestion[]
  answers: WrittenTestAnswer[]
  started_at?: string
  completed_at?: string
}

interface InterviewListItem {
  session_id: string
  resume_id: string
  jd_id: string
  status: string
  current_phase: string
  created_at: string
  started_at?: string
  completed_at?: string
  total_duration: number
  dialogue_count: number
  evaluation_score?: number
  evaluation_recommendation?: string
}

interface Phase {
  name: string
  count: number
}

// State
const interviews = ref<InterviewListItem[]>([])
const selectedId = ref<string>('')
const currentRecord = ref<InterviewRecord | null>(null)
const evaluation = ref<Evaluation | null>(null)
const writtenTest = ref<WrittenTest | null>(null)
const dialogues = ref<DialogueEntry[]>([])
const phases = ref<Phase[]>([])
const dialogueRefs = ref<Map<string, any>>(new Map())
const showWrittenTest = ref<boolean>(false)

const statusFilter = ref<string>('')
const searchQuery = ref<string>('')
const loadingList = ref<boolean>(false)
const loadingDetail = ref<boolean>(false)
const savingHighlight = ref<boolean>(false)

const currentPhase = ref<string>('')

// Phase names mapping - structured interview phases
const phaseNames: Record<string, string> = {
  'opening': '开场',
  'self_intro': '自我介绍',
  'project_deep': '项目深挖',
  'tech_assess': '技术评估',
  'behavioral': '行为面试',
  'qa': '候选人提问',
  'closing': '结束语',
  // Legacy mappings
  'greeting': '开场问候',
  'background': '背景了解',
  'technical': '技术评估',
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
      i.session_id.toLowerCase().includes(query)
    )
  }

  return result
})

// Methods
async function loadInterviews() {
  loadingList.value = true
  try {
    // Use /api/interviews endpoint for structured interview records
    const response = await request.get('/interviews', {
      params: { limit: 100, offset: 0 }
    })
    if (Array.isArray(response.data)) {
      interviews.value = response.data
    } else if (response.data?.data) {
      interviews.value = response.data.data
    }
  } catch (error) {
    console.error('Failed to load interviews:', error)
  } finally {
    loadingList.value = false
  }
}

async function deleteInterview(sessionId: string) {
  if (!confirm('确定要删除这条面试记录吗？此操作不可恢复。')) {
    return
  }

  try {
    await request.delete(`/interviews/${sessionId}`)
    // 从列表中移除
    interviews.value = interviews.value.filter(i => i.session_id !== sessionId)
    // 如果删除的是当前选中的，清空详情
    if (selectedId.value === sessionId) {
      selectedId.value = ''
      currentRecord.value = null
      evaluation.value = null
      writtenTest.value = null
    }
  } catch (error) {
    console.error('Failed to delete interview:', error)
    alert('删除失败，请重试')
  }
}

async function selectInterview(sessionId: string) {
  selectedId.value = sessionId
  loadingDetail.value = true

  try {
    // Load record details from /api/interviews/{session_id}
    const response = await request.get(`/interviews/${sessionId}`)
    const record = response.data?.data || response.data
    currentRecord.value = record

    // Set evaluation from record
    if (record?.evaluation) {
      evaluation.value = record.evaluation
    } else {
      evaluation.value = null
    }

    // Set written test from record
    if (record?.written_test) {
      writtenTest.value = record.written_test
    } else {
      writtenTest.value = null
    }

    // Process dialogues from record
    processDialogues()

  } catch (error) {
    console.error('Failed to load interview details:', error)
    currentRecord.value = null
    evaluation.value = null
    writtenTest.value = null
  } finally {
    loadingDetail.value = false
  }
}

function processDialogues() {
  if (!currentRecord.value?.dialogues) {
    dialogues.value = []
    phases.value = []
    return
  }

  // Dialogues already have phase info from structured interview
  dialogues.value = currentRecord.value.dialogues

  // Build phases list from dialogues
  const phaseCount: Record<string, number> = {}
  for (const d of currentRecord.value.dialogues) {
    phaseCount[d.phase] = (phaseCount[d.phase] || 0) + 1
  }

  // Sort phases by order
  const phaseOrder = ['opening', 'self_intro', 'project_deep', 'tech_assess', 'behavioral', 'qa', 'closing']
  phases.value = phaseOrder
    .filter(p => phaseCount[p])
    .map(name => ({
      name,
      count: phaseCount[name] || 0
    }))
}

async function toggleHighlight(dialogue: DialogueEntry) {
  if (savingHighlight.value) return

  dialogue.is_highlighted = !dialogue.is_highlighted

  // Save to backend using /api/interviews/{session_id}/highlight
  savingHighlight.value = true
  try {
    await request.post(`/interviews/${currentRecord.value!.session_id}/highlight`, null, {
      params: {
        dialogue_id: dialogue.id,
        notes: dialogue.hr_notes || ''
      }
    })
  } catch (error) {
    console.error('Failed to save highlight:', error)
    // Revert on error
    dialogue.is_highlighted = !dialogue.is_highlighted
  } finally {
    savingHighlight.value = false
  }
}

async function saveHighlightNote(dialogue: DialogueEntry) {
  if (!dialogue.is_highlighted) return

  try {
    await request.post(`/interviews/${currentRecord.value!.session_id}/highlight`, null, {
      params: {
        dialogue_id: dialogue.id,
        notes: dialogue.hr_notes || ''
      }
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
    'not_started': 'bg-gray-100 text-gray-700',
    'in_progress': 'bg-blue-100 text-blue-700',
    'completed': 'bg-green-100 text-green-700',
    'error': 'bg-red-100 text-red-700',
    // Legacy statuses
    'pending': 'bg-gray-100 text-gray-700',
    'written_test': 'bg-blue-100 text-blue-700',
    'voice': 'bg-yellow-100 text-yellow-700',
    'cancelled': 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function statusText(status: string): string {
  const texts: Record<string, string> = {
    'not_started': '待开始',
    'in_progress': '面试中',
    'completed': '已完成',
    'error': '异常',
    // Legacy statuses
    'pending': '待开始',
    'written_test': '笔试中',
    'voice': '面试中',
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
  return classes[recommendation] || 'bg-gray-100 text-gray-700'
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

// Written test helper functions
function getAnswerStatus(questionId: string): boolean {
  if (!writtenTest.value?.answers) return false
  const answer = writtenTest.value.answers.find(a => a.question_id === questionId)
  return answer?.is_correct ?? false
}

function getQuestionTypeText(type: string): string {
  const typeMap: Record<string, string> = {
    'single_choice': '单选题',
    'multiple_choice': '多选题',
    'true_false': '判断题',
    'short_answer': '简答题'
  }
  return typeMap[type] || type
}

function getOptionClass(question: WrittenTestQuestion, option: string): string {
  const isCorrect = isCorrectOption(question, option)
  const isUser = isUserAnswer(question.id, option)

  if (isCorrect && isUser) return 'text-green-700 font-medium'
  if (isCorrect) return 'text-green-600'
  if (isUser) return 'text-red-600'
  return 'text-gray-600'
}

function isCorrectOption(question: WrittenTestQuestion, option: string): boolean {
  const correctAnswer = question.correct_answer
  if (Array.isArray(correctAnswer)) {
    return correctAnswer.includes(option)
  }
  return correctAnswer === option
}

function isUserAnswer(questionId: string, option: string): boolean {
  if (!writtenTest.value?.answers) return false
  const answer = writtenTest.value.answers.find(a => a.question_id === questionId)
  if (!answer) return false

  const userAnswer = answer.answer
  if (Array.isArray(userAnswer)) {
    return userAnswer.includes(option)
  }
  return userAnswer === option
}

function getUserAnswer(questionId: string): string {
  if (!writtenTest.value?.answers) return '未作答'
  const answer = writtenTest.value.answers.find(a => a.question_id === questionId)
  if (!answer) return '未作答'

  const userAnswer = answer.answer
  if (Array.isArray(userAnswer)) {
    return userAnswer.join(', ')
  }
  return String(userAnswer)
}

function formatCorrectAnswer(answer: string | string[]): string {
  if (Array.isArray(answer)) {
    return answer.join(', ')
  }
  return String(answer)
}

function getAIEvaluation(questionId: string): string {
  if (!writtenTest.value?.answers) return ''
  const answer = writtenTest.value.answers.find(a => a.question_id === questionId)
  return answer?.ai_evaluation || ''
}

// Lifecycle
const route = useRoute()

onMounted(async () => {
  await loadInterviews()

  // Auto-select interview from URL query param
  const sessionParam = route.query.session as string
  if (sessionParam && interviews.value.length > 0) {
    // Try to find by session_id
    const found = interviews.value.find(i => i.session_id === sessionParam)
    if (found) {
      selectInterview(found.session_id)
    }
  }
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
