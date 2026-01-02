<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">简历解析</h1>

    <el-card class="mb-4">
      <ResumeUploader @success="handleUploadSuccess" />
    </el-card>

    <el-card>
      <template #header>
        <div class="flex justify-between items-center">
          <span>简历列表</span>
          <el-button @click="loadResumes">刷新</el-button>
        </div>
      </template>
      <ResumeList
        :resumes="resumes"
        :loading="loading"
        @view="handleView"
        @delete="handleDelete"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="dialogVisible" title="简历详情" width="600px">
      <template v-if="currentResume">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ currentResume.basic_info.name }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ currentResume.basic_info.phone }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentResume.basic_info.email }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ currentResume.basic_info.gender }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="mt-4 mb-2 font-bold">教育经历</h4>
        <div v-for="edu in currentResume.education" :key="edu.school" class="mb-2">
          {{ edu.school }} - {{ edu.degree }} {{ edu.major }}
        </div>

        <h4 class="mt-4 mb-2 font-bold">工作经历</h4>
        <div v-for="exp in currentResume.experience" :key="exp.company" class="mb-2">
          <strong>{{ exp.company }}</strong> - {{ exp.title }}
          <p class="text-gray-600 text-sm">{{ exp.duties }}</p>
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
