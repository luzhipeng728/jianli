<template>
  <div class="animate-fade-in">
    <!-- Header Actions -->
    <div class="card p-6 mb-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          <div>
            <h3 class="section-title">面试管理</h3>
            <p class="text-sm text-secondary-500">管理和查看面试记录</p>
          </div>
        </div>
        <button @click="showCreateDialog = true" class="btn-primary flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          创建面试
        </button>
      </div>
    </div>

    <!-- Status Tabs -->
    <div class="card mb-6">
      <div class="px-6 py-4 border-b border-secondary-100">
        <div class="flex items-center gap-2">
          <button
            v-for="tab in statusTabs"
            :key="tab.value"
            @click="activeStatus = tab.value"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-lg transition-all',
              activeStatus === tab.value
                ? 'bg-primary-50 text-primary-700 shadow-sm'
                : 'text-secondary-600 hover:bg-secondary-50'
            ]"
          >
            {{ tab.label }}
            <span
              v-if="getCountByStatus(tab.value) > 0"
              :class="[
                'ml-2 px-2 py-0.5 rounded-full text-xs',
                activeStatus === tab.value
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-secondary-100 text-secondary-600'
              ]"
            >
              {{ getCountByStatus(tab.value) }}
            </span>
          </button>
        </div>
      </div>

      <!-- Interview List -->
      <div class="p-6">
        <!-- Loading -->
        <div v-if="loading" class="flex items-center justify-center py-12">
          <div class="flex flex-col items-center gap-4">
            <div class="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
            <span class="text-secondary-500">加载中...</span>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else-if="filteredInterviews.length === 0" class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-secondary-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p class="text-secondary-500 mb-4">暂无面试记录</p>
          <button @click="showCreateDialog = true" class="btn-primary">
            创建首个面试
          </button>
        </div>

        <!-- Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-secondary-200">
                <th class="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">候选人</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">岗位</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">状态</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">创建时间</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">评分</th>
                <th class="px-4 py-3 text-right text-xs font-semibold text-secondary-600 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-secondary-100">
              <tr
                v-for="interview in paginatedInterviews"
                :key="interview.id"
                class="hover:bg-secondary-50 transition-colors"
              >
                <td class="px-4 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                      <svg class="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <span class="text-sm font-medium text-secondary-800">{{ interview.candidate_name || '未知' }}</span>
                  </div>
                </td>
                <td class="px-4 py-4">
                  <span class="text-sm text-secondary-700">{{ interview.jd_title || '-' }}</span>
                </td>
                <td class="px-4 py-4">
                  <span :class="['inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium', getStatusClass(interview.status)]">
                    <span :class="['w-1.5 h-1.5 rounded-full', getStatusDotClass(interview.status)]"></span>
                    {{ getStatusText(interview.status) }}
                  </span>
                </td>
                <td class="px-4 py-4">
                  <span class="text-sm text-secondary-600">{{ formatDate(interview.created_at) }}</span>
                </td>
                <td class="px-4 py-4">
                  <span v-if="interview.evaluation" class="text-sm font-semibold text-primary-600">
                    {{ interview.evaluation.overall_score }}
                  </span>
                  <span v-else class="text-sm text-secondary-400">-</span>
                </td>
                <td class="px-4 py-4">
                  <div class="flex items-center justify-end gap-2">
                    <button
                      @click="viewDetail(interview)"
                      class="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="查看详情"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button
                      v-if="interview.status === 'completed'"
                      @click="openReplay(interview)"
                      class="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                      title="查看回放"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                    <button
                      @click="copyInterviewLink(interview)"
                      class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="复制链接"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                    </button>
                    <button
                      v-if="interview.status !== 'cancelled' && interview.status !== 'completed'"
                      @click="handleCancel(interview)"
                      class="p-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                      title="取消面试"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                    <button
                      @click="handleDelete(interview)"
                      class="p-2 text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                      title="删除面试"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="filteredInterviews.length > 0" class="flex items-center justify-between mt-6 pt-4 border-t border-secondary-100">
          <span class="text-sm text-secondary-500">共 {{ filteredInterviews.length }} 条记录</span>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredInterviews.length"
            layout="sizes, prev, pager, next, jumper"
          />
        </div>
      </div>
    </div>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="detailDrawerVisible"
      title=""
      size="600px"
      :show-close="true"
    >
      <template #header>
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div>
            <h2 class="text-xl font-bold text-secondary-900">面试详情</h2>
            <p class="text-sm text-secondary-500">{{ currentInterview?.candidate_name || '查看面试信息' }}</p>
          </div>
        </div>
      </template>

      <InterviewDetail v-if="currentInterview" :interview="currentInterview" />
    </el-drawer>

    <!-- Create Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建面试"
      width="500px"
    >
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="简历">
          <el-select v-model="createForm.resume_id" placeholder="选择简历" class="w-full">
            <el-option
              v-for="resume in resumeOptions"
              :key="resume.id"
              :label="resume.basic_info?.name || resume.file_name"
              :value="resume.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位">
          <el-select v-model="createForm.jd_id" placeholder="选择岗位" class="w-full">
            <el-option
              v-for="jd in jdOptions"
              :key="jd.id"
              :label="jd.title"
              :value="jd.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-3">
          <button @click="showCreateDialog = false" class="btn-secondary" :disabled="creating">
            取消
          </button>
          <button @click="handleCreate" class="btn-primary" :disabled="!createForm.resume_id || !createForm.jd_id || creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import InterviewDetail from '@/components/interview/InterviewDetail.vue'
import { getInterviewList, cancelInterview, deleteInterview, createInterview, type InterviewSession } from '@/api/interview'
import { getResumeList, type ResumeData } from '@/api/resume'
import { getJDList, type JobDescription } from '@/api/jd'

const interviews = ref<InterviewSession[]>([])
const loading = ref(false)
const activeStatus = ref<string>('all')
const currentPage = ref(1)
const pageSize = ref(20)
const detailDrawerVisible = ref(false)
const currentInterview = ref<InterviewSession | null>(null)
const showCreateDialog = ref(false)
const resumeOptions = ref<ResumeData[]>([])
const jdOptions = ref<JobDescription[]>([])
const creating = ref(false)

const createForm = ref({
  resume_id: '',
  jd_id: ''
})

const statusTabs = [
  { label: '全部', value: 'all' },
  { label: '待面试', value: 'pending' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' }
]

const filteredInterviews = computed(() => {
  if (activeStatus.value === 'all') return interviews.value
  if (activeStatus.value === 'in_progress') {
    return interviews.value.filter(i => i.status === 'written_test' || i.status === 'voice')
  }
  return interviews.value.filter(i => i.status === activeStatus.value)
})

const paginatedInterviews = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredInterviews.value.slice(start, end)
})

const getCountByStatus = (status: string) => {
  if (status === 'all') return interviews.value.length
  if (status === 'in_progress') {
    return interviews.value.filter(i => i.status === 'written_test' || i.status === 'voice').length
  }
  return interviews.value.filter(i => i.status === status).length
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待面试',
    written_test: '笔试中',
    voice: '语音面试中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

const getStatusClass = (status: string) => {
  const classMap: Record<string, string> = {
    pending: 'bg-secondary-100 text-secondary-700',
    written_test: 'bg-blue-100 text-blue-700',
    voice: 'bg-purple-100 text-purple-700',
    completed: 'bg-success-100 text-success-700',
    cancelled: 'bg-danger-100 text-danger-700'
  }
  return classMap[status] || 'bg-secondary-100 text-secondary-700'
}

const getStatusDotClass = (status: string) => {
  const classMap: Record<string, string> = {
    pending: 'bg-secondary-500',
    written_test: 'bg-blue-500',
    voice: 'bg-purple-500',
    completed: 'bg-success-500',
    cancelled: 'bg-danger-500'
  }
  return classMap[status] || 'bg-secondary-500'
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadInterviews = async () => {
  loading.value = true
  try {
    const result = await getInterviewList(1, 100)
    interviews.value = result.data || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const loadResumeOptions = async () => {
  try {
    const result = await getResumeList(1, 100)
    resumeOptions.value = result.data || []
  } catch (error: any) {
    console.error('Failed to load resumes:', error)
  }
}

const loadJDOptions = async () => {
  try {
    const result = await getJDList(1, 100)
    jdOptions.value = result.data || []
  } catch (error: any) {
    console.error('Failed to load JDs:', error)
  }
}

const viewDetail = async (interview: InterviewSession) => {
  currentInterview.value = interview
  detailDrawerVisible.value = true
}

const copyInterviewLink = (interview: InterviewSession) => {
  const baseUrl = window.location.origin
  const url = `${baseUrl}/interview/${interview.token}`
  navigator.clipboard.writeText(url)
  ElMessage.success('面试链接已复制到剪贴板')
}

const openReplay = (interview: InterviewSession) => {
  // Open HR replay page in new tab
  // The interview token is used as session_id in the structured interview system
  const replayUrl = `/interview/hr/replay?session=${interview.token}`
  window.open(replayUrl, '_blank')
}

const handleCancel = async (interview: InterviewSession) => {
  try {
    await ElMessageBox.confirm('确定要取消这个面试吗？', '提示', {
      type: 'warning'
    })
    await cancelInterview(interview.id)
    ElMessage.success('面试已取消')
    loadInterviews()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '取消失败')
    }
  }
}

const handleDelete = async (interview: InterviewSession) => {
  try {
    await ElMessageBox.confirm('确定要永久删除这个面试记录吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确认删除',
      confirmButtonClass: 'el-button--danger'
    })
    await deleteInterview(interview.id)
    ElMessage.success('面试已删除')
    loadInterviews()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleCreate = async () => {
  if (creating.value) return
  creating.value = true
  try {
    await createInterview(createForm.value.resume_id, createForm.value.jd_id)
    ElMessage.success('面试创建成功')
    showCreateDialog.value = false
    createForm.value = { resume_id: '', jd_id: '' }
    loadInterviews()
  } catch (error: any) {
    ElMessage.error(error.message || '创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadInterviews()
  loadResumeOptions()
  loadJDOptions()
})
</script>
