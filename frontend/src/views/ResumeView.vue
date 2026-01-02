<template>
  <div class="animate-fade-in">
    <!-- Upload Section -->
    <div class="card p-6 mb-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center">
          <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <div>
          <h3 class="section-title">上传简历</h3>
          <p class="text-sm text-secondary-500">支持 PDF、Word、TXT、图片格式</p>
        </div>
      </div>
      <ResumeUploader @success="handleUploadSuccess" />
    </div>

    <!-- Resume List Section -->
    <div class="card">
      <div class="px-6 py-4 border-b border-secondary-100 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-secondary-100 flex items-center justify-center">
            <svg class="w-4 h-4 text-secondary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 class="font-semibold text-secondary-800">简历列表</h3>
            <p class="text-xs text-secondary-500">共 {{ resumes.length }} 份简历</p>
          </div>
        </div>
        <button @click="loadResumes" class="btn-secondary flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          刷新
        </button>
      </div>
      <div class="p-6">
        <ResumeList
          :resumes="resumes"
          :loading="loading"
          @view="handleView"
          @delete="handleDelete"
        />
      </div>
    </div>

    <!-- Detail Dialog -->
    <el-dialog
      v-model="dialogVisible"
      title=""
      width="700px"
      :show-close="true"
      class="resume-dialog"
    >
      <template #header>
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div>
            <h2 class="text-xl font-bold text-secondary-900">{{ currentResume?.basic_info?.name || '简历详情' }}</h2>
            <p class="text-sm text-secondary-500">{{ currentResume?.file_name }}</p>
          </div>
        </div>
      </template>

      <template v-if="currentResume">
        <!-- Basic Info -->
        <div class="card p-4 mb-4">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">基本信息</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.phone || '-' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.email || '-' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.gender || '-' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.age ? `${currentResume.basic_info.age}岁` : '-' }}</span>
            </div>
          </div>
        </div>

        <!-- Education -->
        <div class="card p-4 mb-4" v-if="currentResume.education?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">教育经历</h4>
          <div class="space-y-3">
            <div v-for="edu in currentResume.education" :key="edu.school" class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg class="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M12 14l9-5-9-5-9 5 9 5z" /><path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                </svg>
              </div>
              <div>
                <p class="font-medium text-secondary-800">{{ edu.school }}</p>
                <p class="text-sm text-secondary-500">{{ edu.degree }} · {{ edu.major }}</p>
                <p class="text-xs text-secondary-400" v-if="edu.start_date || edu.end_date">{{ edu.start_date }} - {{ edu.end_date }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Experience -->
        <div class="card p-4 mb-4" v-if="currentResume.experience?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">工作经历</h4>
          <div class="space-y-4">
            <div v-for="exp in currentResume.experience" :key="exp.company" class="border-l-2 border-primary-200 pl-4">
              <p class="font-medium text-secondary-800">{{ exp.company }}</p>
              <p class="text-sm text-primary-600">{{ exp.title }}</p>
              <p class="text-xs text-secondary-400 mb-2" v-if="exp.start_date || exp.end_date">{{ exp.start_date }} - {{ exp.end_date }}</p>
              <p class="text-sm text-secondary-600 whitespace-pre-line">{{ exp.duties }}</p>
            </div>
          </div>
        </div>

        <!-- Skills -->
        <div class="card p-4" v-if="currentResume.skills?.hard_skills?.length || currentResume.skills?.soft_skills?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">技能标签</h4>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="skill in currentResume.skills?.hard_skills"
              :key="skill"
              class="px-3 py-1 rounded-full text-sm bg-primary-50 text-primary-700"
            >
              {{ skill }}
            </span>
            <span
              v-for="skill in currentResume.skills?.soft_skills"
              :key="skill"
              class="px-3 py-1 rounded-full text-sm bg-secondary-100 text-secondary-700"
            >
              {{ skill }}
            </span>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ResumeUploader from '@/components/resume/ResumeUploader.vue'
import ResumeList from '@/components/resume/ResumeList.vue'
import { getResumeList, deleteResume, type ResumeData } from '@/api/resume'

const resumes = ref<ResumeData[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentResume = ref<ResumeData | null>(null)

const loadResumes = async () => {
  loading.value = true
  try {
    const result = await getResumeList()
    resumes.value = result.data || []
  } finally {
    loading.value = false
  }
}

const handleUploadSuccess = (data: ResumeData) => {
  resumes.value.unshift(data)
}

const handleView = (resume: ResumeData) => {
  currentResume.value = resume
  dialogVisible.value = true
}

const handleDelete = async (id: string) => {
  await ElMessageBox.confirm('确定删除这份简历？', '提示')
  await deleteResume(id)
  ElMessage.success('删除成功')
  resumes.value = resumes.value.filter(r => r.id !== id)
}

onMounted(loadResumes)
</script>

<style>
.resume-dialog .el-dialog__header {
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  margin-right: 0;
}

.resume-dialog .el-dialog__body {
  padding: 24px;
  max-height: 70vh;
  overflow-y: auto;
}
</style>
