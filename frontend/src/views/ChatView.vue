<template>
  <div class="animate-fade-in h-[calc(100vh-140px)] flex flex-col">
    <div class="card flex-1 flex flex-col overflow-hidden min-h-0">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-secondary-100 flex items-center justify-between flex-shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <div>
            <h3 class="font-semibold text-secondary-800">AI 智能助手</h3>
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-success-500"></span>
              <span class="text-xs text-secondary-500">在线</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <!-- JD Selector with Prompt -->
          <div class="flex items-center gap-2">
            <div v-if="!chatJdId" class="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
              选择岗位获得更精准回答
            </div>
            <el-select
              v-model="chatJdId"
              placeholder="选择岗位"
              clearable
              class="min-w-48"
              size="default"
              style="min-width: 200px;"
            >
              <el-option
                v-for="jd in jdList"
                :key="jd.id"
                :label="jd.title"
                :value="jd.id"
              >
                <span class="truncate">{{ jd.title }}</span>
              </el-option>
            </el-select>
          </div>
          <button @click="clearChat" class="btn-secondary flex items-center gap-2 px-4">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>新建会话</span>
          </button>
        </div>
      </div>

      <!-- Chat Window -->
      <ChatWindow ref="chatWindowRef" :jd-id="chatJdId" class="flex-1 min-h-0 overflow-hidden" @candidate-click="handleCandidateClick" />
    </div>

    <!-- Candidate Detail Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="selectedCandidate?.name || '候选人详情'"
      width="800px"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
    >
      <div v-if="selectedCandidate" class="space-y-6">
        <!-- Basic Info -->
        <div class="flex items-center gap-4 pb-4 border-b border-secondary-100">
          <div class="w-16 h-16 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white text-2xl font-semibold">
            {{ selectedCandidate.name?.charAt(0) || '?' }}
          </div>
          <div class="flex-1">
            <h3 class="text-xl font-semibold text-secondary-900 mb-1">{{ selectedCandidate.name }}</h3>
            <p class="text-secondary-600">{{ selectedCandidate.title || '开发工程师' }}</p>
            <div v-if="selectedCandidate.match_score" class="mt-2">
              <span class="px-2 py-1 rounded text-sm font-medium" :class="selectedCandidate.match_score >= 80 ? 'bg-green-100 text-green-700' : selectedCandidate.match_score >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-secondary-100 text-secondary-600'">
                匹配度: {{ selectedCandidate.match_score }}%
              </span>
            </div>
          </div>
        </div>

        <!-- Contact Info -->
        <div>
          <h4 class="text-base font-semibold text-secondary-800 mb-3 flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            基本信息
          </h4>
          <div class="grid grid-cols-2 gap-3 bg-secondary-50 rounded-lg p-4">
            <div v-if="selectedCandidate.company" class="flex items-center gap-2">
              <span class="text-secondary-500 text-sm">当前公司:</span>
              <span class="text-secondary-800 text-sm font-medium">{{ selectedCandidate.company }}</span>
            </div>
            <div v-if="selectedCandidate.experience_years" class="flex items-center gap-2">
              <span class="text-secondary-500 text-sm">工作经验:</span>
              <span class="text-secondary-800 text-sm font-medium">{{ selectedCandidate.experience_years }}年</span>
            </div>
          </div>
        </div>

        <!-- Education -->
        <div v-if="selectedCandidate.education">
          <h4 class="text-base font-semibold text-secondary-800 mb-3 flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            教育经历
          </h4>
          <div class="bg-secondary-50 rounded-lg p-4">
            <p class="text-secondary-700">{{ selectedCandidate.education }}</p>
          </div>
        </div>

        <!-- Skills -->
        <div v-if="selectedCandidate.skills && selectedCandidate.skills.length > 0">
          <h4 class="text-base font-semibold text-secondary-800 mb-3 flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            技能
          </h4>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="skill in selectedCandidate.skills"
              :key="skill"
              class="px-3 py-1.5 bg-primary-50 text-primary-700 rounded-lg text-sm font-medium"
            >
              {{ skill }}
            </span>
          </div>
        </div>

        <!-- Highlights -->
        <div v-if="selectedCandidate.highlights && selectedCandidate.highlights.length > 0">
          <h4 class="text-base font-semibold text-secondary-800 mb-3 flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            亮点
          </h4>
          <ul class="space-y-2">
            <li
              v-for="(highlight, idx) in selectedCandidate.highlights"
              :key="idx"
              class="flex items-start gap-2 text-secondary-700"
            >
              <svg class="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{{ highlight }}</span>
            </li>
          </ul>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-between items-center">
          <el-button type="primary" size="large" @click="showInviteDialog">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            发起面试邀请
          </el-button>
          <el-button size="large" @click="dialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Interview Invite Dialog -->
    <el-dialog
      v-model="inviteDialogVisible"
      title="发起面试邀请"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="space-y-4">
        <div v-if="!interviewLink">
          <p class="text-secondary-600 mb-4">请选择要面试的岗位：</p>
          <el-select
            v-model="selectedJdId"
            placeholder="请选择岗位"
            class="w-full"
            size="large"
            :loading="loadingJds"
          >
            <el-option
              v-for="jd in jdList"
              :key="jd.id"
              :label="jd.title"
              :value="jd.id"
            />
          </el-select>
          <p v-if="jdList.length === 0 && !loadingJds" class="text-secondary-500 text-sm mt-2">
            暂无岗位，请先在 <router-link to="/jd" class="text-primary-600 hover:underline">岗位管理</router-link> 中创建岗位
          </p>
        </div>
        <div v-else class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-secondary-900 mb-2">面试邀请已创建</h3>
          <p class="text-secondary-600 mb-4">请将以下链接发送给候选人：</p>
          <div class="bg-secondary-50 rounded-lg p-3 flex items-center gap-2">
            <input
              type="text"
              :value="interviewLink"
              readonly
              class="flex-1 bg-transparent border-none outline-none text-sm text-secondary-700"
            />
            <el-button type="primary" size="small" @click="copyLink">
              复制链接
            </el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="closeInviteDialog">{{ interviewLink ? '完成' : '取消' }}</el-button>
          <el-button
            v-if="!interviewLink"
            type="primary"
            :loading="creating"
            :disabled="!selectedJdId"
            @click="createInterviewInvite"
          >
            创建邀请
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ChatWindow from '@/components/chat/ChatWindow.vue'
import { createInterview } from '@/api/interview'
import { getJDList } from '@/api/jd'

const chatWindowRef = ref()
const dialogVisible = ref(false)
const selectedCandidate = ref<any>(null)

// JD filter for chat
const chatJdId = ref('')

// Interview invite
const inviteDialogVisible = ref(false)
const selectedJdId = ref('')
const jdList = ref<any[]>([])
const loadingJds = ref(false)
const creating = ref(false)
const interviewLink = ref('')

const clearChat = () => {
  location.reload()
}

const handleCandidateClick = (candidate: any) => {
  selectedCandidate.value = candidate
  dialogVisible.value = true
}

const loadJdList = async () => {
  loadingJds.value = true
  try {
    const result = await getJDList(1, 100)
    jdList.value = result.data || []
  } catch (error: any) {
    ElMessage.error('加载岗位列表失败')
  } finally {
    loadingJds.value = false
  }
}

const showInviteDialog = () => {
  if (!selectedCandidate.value?.resume_id) {
    ElMessage.warning('无法获取候选人信息，请重新搜索')
    return
  }
  inviteDialogVisible.value = true
  interviewLink.value = ''
  selectedJdId.value = ''
  loadJdList()
}

const createInterviewInvite = async () => {
  if (!selectedJdId.value || !selectedCandidate.value?.resume_id) {
    return
  }
  creating.value = true
  try {
    const result: any = await createInterview(selectedCandidate.value.resume_id, selectedJdId.value)
    const token = result?.token || result?.data?.token
    if (token) {
      interviewLink.value = `${window.location.origin}/interview/${token}`
      ElMessage.success('面试邀请创建成功')
    } else {
      throw new Error('创建失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '创建面试邀请失败')
  } finally {
    creating.value = false
  }
}

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(interviewLink.value)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

const closeInviteDialog = () => {
  inviteDialogVisible.value = false
  interviewLink.value = ''
  selectedJdId.value = ''
}

onMounted(() => {
  // Pre-load JD list
  loadJdList()
})
</script>
