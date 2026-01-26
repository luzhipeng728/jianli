<template>
  <div class="batch-uploader">
    <!-- 上传区域 -->
    <div
      v-if="!batchId"
      class="upload-area"
      :class="{ 'upload-area-active': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        multiple
        accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png"
        @change="handleFileChange"
      />

      <div class="flex flex-col items-center gap-4 py-8">
        <div :class="[
          'w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300',
          isDragging ? 'bg-primary-100 scale-110' : 'bg-primary-50'
        ]">
          <svg class="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>

        <div class="text-center">
          <p class="text-secondary-700 font-medium">
            拖拽多个文件到此处，或
            <span class="text-primary-600 hover:text-primary-700 cursor-pointer">点击选择</span>
          </p>
          <p class="text-sm text-secondary-400 mt-1">后台自动处理，最多100个文件，支持10并发</p>
        </div>

        <div class="flex items-center gap-4 mt-2">
          <div class="flex items-center gap-1 text-xs text-secondary-400">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/></svg>
            PDF
          </div>
          <div class="flex items-center gap-1 text-xs text-secondary-400">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/></svg>
            Word
          </div>
          <div class="flex items-center gap-1 text-xs text-secondary-400">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2z"/></svg>
            图片
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="selectedFile" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="selectedFile = null">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden">
        <div class="flex items-center justify-between p-4 border-b border-secondary-100">
          <h3 class="font-semibold text-secondary-800">简历解析详情</h3>
          <button @click="selectedFile = null" class="p-1 hover:bg-secondary-100 rounded-lg transition-colors">
            <svg class="w-5 h-5 text-secondary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="p-4 overflow-y-auto max-h-[calc(80vh-60px)]">
          <!-- 文件信息 -->
          <div class="mb-4">
            <p class="text-sm text-secondary-500 mb-1">文件名</p>
            <p class="font-medium text-secondary-800">{{ selectedFile.file_name }}</p>
          </div>

          <!-- 状态 -->
          <div class="mb-4">
            <p class="text-sm text-secondary-500 mb-1">状态</p>
            <div class="flex items-center gap-2">
              <span v-if="selectedFile.status === 'success' && !selectedFile.result?.warnings_count"
                class="px-2 py-1 bg-green-100 text-green-700 text-sm rounded-lg">解析成功</span>
              <span v-else-if="selectedFile.status === 'success' && selectedFile.result?.warnings_count"
                class="px-2 py-1 bg-yellow-100 text-yellow-700 text-sm rounded-lg">有风险警告</span>
              <span v-else-if="selectedFile.status === 'failed'"
                class="px-2 py-1 bg-red-100 text-red-700 text-sm rounded-lg">解析失败</span>
              <span v-else class="px-2 py-1 bg-secondary-100 text-secondary-600 text-sm rounded-lg">{{ selectedFile.status }}</span>
            </div>
          </div>

          <!-- 基本信息 -->
          <div v-if="selectedFile.result" class="mb-4">
            <p class="text-sm text-secondary-500 mb-2">基本信息</p>
            <div class="bg-secondary-50 rounded-xl p-3 space-y-2">
              <div v-if="selectedFile.result.name" class="flex">
                <span class="text-secondary-500 w-16">姓名:</span>
                <span class="text-secondary-800 font-medium">{{ selectedFile.result.name }}</span>
              </div>
              <div v-if="selectedFile.result.phone" class="flex">
                <span class="text-secondary-500 w-16">电话:</span>
                <span class="text-secondary-800">{{ selectedFile.result.phone }}</span>
              </div>
              <div v-if="selectedFile.result.email" class="flex">
                <span class="text-secondary-500 w-16">邮箱:</span>
                <span class="text-secondary-800">{{ selectedFile.result.email }}</span>
              </div>
            </div>
          </div>

          <!-- 技能标签 -->
          <div v-if="selectedFile.result?.skills?.length" class="mb-4">
            <p class="text-sm text-secondary-500 mb-2">技能</p>
            <div class="flex flex-wrap gap-2">
              <span v-for="skill in selectedFile.result.skills" :key="skill"
                class="px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-lg">{{ skill }}</span>
            </div>
          </div>

          <!-- LLM输出 -->
          <div v-if="selectedFile.llm_output" class="mb-4">
            <p class="text-sm text-secondary-500 mb-2">AI分析过程</p>
            <div class="bg-secondary-900 rounded-xl p-3 max-h-48 overflow-y-auto">
              <pre class="text-green-400 text-xs whitespace-pre-wrap break-all">{{ selectedFile.llm_output }}</pre>
            </div>
          </div>

          <!-- 风险警告 -->
          <div v-if="selectedFile.result?.warnings?.length" class="mb-4">
            <p class="text-sm text-secondary-500 mb-2">风险警告 ({{ selectedFile.result.warnings_count }})</p>
            <div class="space-y-2">
              <div v-for="(warning, index) in selectedFile.result.warnings" :key="index"
                class="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-xl">
                <svg class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <p class="text-sm font-medium text-yellow-800">{{ warning.type }}</p>
                  <p class="text-sm text-yellow-700">{{ warning.message }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 错误信息 -->
          <div v-if="selectedFile.error" class="mb-4">
            <p class="text-sm text-secondary-500 mb-2">错误信息</p>
            <div class="p-3 bg-red-50 border border-red-200 rounded-xl">
              <p class="text-sm text-red-700">{{ selectedFile.error }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 已选择文件列表 -->
    <div v-if="selectedFiles.length > 0 && !batchId" class="mt-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm font-medium text-secondary-700">已选择 {{ selectedFiles.length }} 个文件</span>
        <button @click="clearFiles" class="text-sm text-secondary-500 hover:text-secondary-700">清空</button>
      </div>

      <div class="max-h-48 overflow-y-auto space-y-2">
        <div
          v-for="file in selectedFiles"
          :key="file.name"
          class="flex items-center justify-between p-2 bg-secondary-50 rounded-lg"
        >
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-secondary-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
            </svg>
            <span class="text-sm text-secondary-700 truncate max-w-xs">{{ file.name }}</span>
          </div>
          <span class="text-xs text-secondary-400">{{ formatSize(file.size) }}</span>
        </div>
      </div>

      <button
        @click="startUpload"
        :disabled="isUploading"
        class="mt-4 w-full py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{ isUploading ? '上传中...' : `开始上传 (${selectedFiles.length} 个文件)` }}
      </button>
    </div>

    <!-- 处理进度 - 紧凑设计 -->
    <div v-if="batchId" class="mt-4">
      <!-- 顶部状态栏 -->
      <div class="bg-secondary-50 rounded-xl p-4 mb-4">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-10 h-10 rounded-xl flex items-center justify-center',
              isProcessing ? 'bg-primary-100' : (batchStatus === 'success' ? 'bg-green-100' : 'bg-amber-100')
            ]">
              <div v-if="isProcessing" class="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
              <svg v-else-if="batchStatus === 'success'" class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <svg v-else class="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </div>
            <div>
              <p class="font-semibold text-secondary-800">
                {{ isProcessing ? '批量解析中' : (batchStatus === 'success' ? '解析完成' : '解析完成') }}
              </p>
              <p class="text-xs text-secondary-500">
                {{ completedCount + failedCount }}/{{ totalCount }} 已处理
                <span v-if="processingCount > 0" class="text-primary-600 ml-1">· {{ processingCount }} 并发中</span>
              </p>
            </div>
          </div>
          <div class="text-right">
            <p class="text-2xl font-bold text-secondary-800">{{ overallProgress }}%</p>
          </div>
        </div>

        <!-- 进度条 -->
        <div class="relative h-2 bg-secondary-200 rounded-full overflow-hidden">
          <div class="absolute inset-y-0 left-0 bg-green-500 transition-all duration-300" :style="{ width: `${(successCount / totalCount) * 100}%` }"></div>
          <div class="absolute inset-y-0 bg-amber-500 transition-all duration-300" :style="{ left: `${(successCount / totalCount) * 100}%`, width: `${(warningCount / totalCount) * 100}%` }"></div>
          <div class="absolute inset-y-0 bg-red-500 transition-all duration-300" :style="{ left: `${((successCount + warningCount) / totalCount) * 100}%`, width: `${(failedCount / totalCount) * 100}%` }"></div>
          <div v-if="isProcessing" class="absolute inset-y-0 progress-bar-stripe transition-all duration-300" :style="{ left: `${((successCount + warningCount + failedCount) / totalCount) * 100}%`, width: `${(processingFiles.length / totalCount) * 100}%` }"></div>
        </div>

        <!-- 统计标签 -->
        <div class="flex items-center gap-4 mt-3 text-xs">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            <span class="text-secondary-600">成功 {{ successCount }}</span>
          </div>
          <div v-if="warningCount > 0" class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-amber-500"></span>
            <span class="text-secondary-600">警告 {{ warningCount }}</span>
          </div>
          <div v-if="failedCount > 0" class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-red-500"></span>
            <span class="text-secondary-600">失败 {{ failedCount }}</span>
          </div>
          <div v-if="queuedCount > 0" class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-secondary-400"></span>
            <span class="text-secondary-600">等待 {{ queuedCount }}</span>
          </div>
        </div>
      </div>

      <!-- 紧凑文件列表 -->
      <div class="border border-secondary-200 rounded-xl overflow-hidden">
        <!-- 表头 -->
        <div class="grid grid-cols-12 gap-2 px-3 py-2 bg-secondary-100 text-xs font-medium text-secondary-600 uppercase">
          <div class="col-span-5">文件名</div>
          <div class="col-span-3">状态</div>
          <div class="col-span-3">结果</div>
          <div class="col-span-1 text-center">操作</div>
        </div>

        <!-- 文件行 - 虚拟滚动容器 -->
        <div class="max-h-72 overflow-y-auto divide-y divide-secondary-100">
          <div
            v-for="file in fileStatuses"
            :key="file.file_id"
            class="grid grid-cols-12 gap-2 px-3 py-2 items-center hover:bg-secondary-50 transition-colors cursor-pointer"
            @click="showFileDetail(file)"
          >
            <!-- 文件名 -->
            <div class="col-span-5 flex items-center gap-2 min-w-0">
              <div class="flex-shrink-0">
                <svg v-if="file.status === 'success'" class="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <svg v-else-if="file.status === 'failed'" class="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
                <div v-else-if="file.status === 'processing' || file.status === 'retrying'" class="w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                <svg v-else class="w-4 h-4 text-secondary-300" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
                </svg>
              </div>
              <span class="text-sm text-secondary-700 truncate">{{ file.file_name }}</span>
            </div>

            <!-- 状态 -->
            <div class="col-span-3">
              <span v-if="file.status === 'processing'" class="inline-flex items-center gap-1 text-xs text-primary-600">
                <span class="truncate">{{ file.status_detail || '处理中' }}</span>
                <span class="text-primary-400">{{ file.progress }}%</span>
              </span>
              <span v-else-if="file.status === 'retrying'" class="text-xs text-amber-600">重试 #{{ file.retry_count }}</span>
              <span v-else-if="file.status === 'queued'" class="text-xs text-secondary-500">等待中</span>
              <span v-else-if="file.status === 'success' && file.result?.warnings_count" class="text-xs text-amber-600">{{ file.result.warnings_count }}个警告</span>
              <span v-else-if="file.status === 'success'" class="text-xs text-green-600">完成</span>
              <span v-else-if="file.status === 'failed'" class="text-xs text-red-500 truncate">{{ file.error || '失败' }}</span>
            </div>

            <!-- 结果 -->
            <div class="col-span-3">
              <span v-if="file.result?.name" class="text-sm text-secondary-700 truncate block">{{ file.result.name }}</span>
              <span v-else class="text-xs text-secondary-400">-</span>
            </div>

            <!-- 操作 -->
            <div class="col-span-1 text-center">
              <svg v-if="file.status === 'success' || file.status === 'failed'" class="w-4 h-4 text-secondary-400 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex gap-3 mt-4">
        <button
          v-if="failedCount > 0 && !isProcessing"
          @click="handleRetry"
          class="flex-1 py-2.5 border border-primary-500 text-primary-600 rounded-xl font-medium hover:bg-primary-50 transition-colors"
        >
          重试失败 ({{ failedCount }})
        </button>
        <button
          @click="resetUploader"
          class="flex-1 py-2.5 bg-secondary-100 text-secondary-700 rounded-xl font-medium hover:bg-secondary-200 transition-colors"
        >
          {{ isProcessing ? '关闭' : '上传更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createBatchTask,
  getBatchStatus,
  retryFailed as apiRetryFailed,
  pollBatchStatus,
  type FileInfo,
  type BatchTask
} from '@/api/batch'

const emit = defineEmits<{
  (e: 'success', data: { total: number; success: number; failed: number }): void
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const selectedFiles = ref<File[]>([])
const isUploading = ref(false)
const isProcessing = ref(false)

const batchId = ref<string | null>(null)
const totalCount = ref(0)
const completedCount = ref(0)
const failedCount = ref(0)
const processingCount = ref(0)
const batchStatus = ref<string>('pending')
const fileStatuses = ref<FileInfo[]>([])
const selectedFile = ref<FileInfo | null>(null)

// 轮询控制器
let pollController: { stop: () => void } | null = null

// localStorage key for batch persistence
const BATCH_STORAGE_KEY = 'active_batch_id'

const overallProgress = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((completedCount.value + failedCount.value) / totalCount.value * 100)
})

const successCount = computed(() => {
  return fileStatuses.value.filter(f => f.status === 'success' && !f.result?.warnings_count).length
})

const warningCount = computed(() => {
  return fileStatuses.value.filter(f => f.status === 'success' && f.result?.warnings_count).length
})

const processingFiles = computed(() => {
  return fileStatuses.value.filter(f => f.status === 'processing')
})

const queuedCount = computed(() => {
  return fileStatuses.value.filter(f => f.status === 'queued' || f.status === 'pending').length
})

const showFileDetail = (file: FileInfo) => {
  if (file.status === 'success' || file.status === 'failed') {
    selectedFile.value = file
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  addFiles(files)
  target.value = ''
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  addFiles(files)
}

const addFiles = (files: File[]) => {
  const validExtensions = ['.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.bmp', '.webp']

  for (const file of files) {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!validExtensions.includes(ext)) {
      ElMessage.warning(`不支持的格式: ${file.name}`)
      continue
    }

    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning(`文件过大: ${file.name}`)
      continue
    }

    if (selectedFiles.value.some(f => f.name === file.name)) {
      continue
    }

    selectedFiles.value.push(file)
  }

  if (selectedFiles.value.length > 100) {
    selectedFiles.value = selectedFiles.value.slice(0, 100)
    ElMessage.warning('最多选择100个文件')
  }
}

const clearFiles = () => {
  selectedFiles.value = []
}

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const startUpload = async () => {
  if (selectedFiles.value.length === 0) return

  isUploading.value = true

  try {
    // 创建批量任务（上传后自动开始后台处理）
    const result = await createBatchTask(selectedFiles.value)
    batchId.value = result.batch_id
    totalCount.value = result.total_files
    fileStatuses.value = result.files.map(f => ({
      file_id: f.file_id,
      file_name: f.file_name,
      status: 'queued' as const,
      progress: 0,
      retry_count: 0,
      updated_at: new Date().toISOString()
    }))

    selectedFiles.value = []
    isUploading.value = false
    isProcessing.value = true

    // 保存batchId到localStorage，以便刷新后恢复
    localStorage.setItem(BATCH_STORAGE_KEY, result.batch_id)

    // 显示跳过的文件提示
    if (result.skipped && result.skipped.length > 0) {
      const skippedNames = result.skipped.map((s: any) => `${s.file}(${s.reason})`).join(', ')
      ElMessage.warning(`跳过 ${result.skipped.length} 个无效文件: ${skippedNames}`)
    }

    ElMessage.success(result.message || '文件已上传，后台正在处理...')

    // 开始轮询进度
    startPolling(result.batch_id)

  } catch (error: any) {
    ElMessage.error(error.message || '上传失败')
    isUploading.value = false
    isProcessing.value = false
  }
}

const startPolling = (id: string) => {
  // 停止之前的轮询
  pollController?.stop()

  pollController = pollBatchStatus(id, (batch: BatchTask) => {
    updateFromBatch(batch)
  }, 2000)
}

const updateFromBatch = (batch: BatchTask) => {
  batchStatus.value = batch.status
  totalCount.value = batch.total
  completedCount.value = batch.completed
  failedCount.value = batch.failed
  processingCount.value = batch.processing || 0
  fileStatuses.value = batch.files

  // 检查是否完成
  if (batch.status === 'success' || batch.status === 'failed') {
    isProcessing.value = false
    pollController?.stop()
    // 批量任务完成，清理localStorage
    localStorage.removeItem(BATCH_STORAGE_KEY)

    emit('success', {
      total: batch.total,
      success: batch.completed,
      failed: batch.failed
    })

    if (batch.failed === 0) {
      const warningFiles = batch.files.filter(f => f.result?.warnings_count).length
      if (warningFiles > 0) {
        ElMessage.warning(`处理完成，共 ${batch.completed} 份，其中 ${warningFiles} 份有风险警告`)
      } else {
        ElMessage.success(`全部处理完成，共 ${batch.completed} 份简历`)
      }
    } else {
      ElMessage.warning(`处理完成: ${batch.completed} 成功, ${batch.failed} 失败`)
    }
  }
}

const handleRetry = async () => {
  if (!batchId.value || isProcessing.value) return

  try {
    await apiRetryFailed(batchId.value)
    isProcessing.value = true
    ElMessage.success('已开始重试失败的文件')

    // 重新开始轮询
    startPolling(batchId.value)
  } catch (error: any) {
    ElMessage.error(error.message || '重试失败')
  }
}

const resetUploader = () => {
  pollController?.stop()
  pollController = null

  batchId.value = null
  totalCount.value = 0
  completedCount.value = 0
  failedCount.value = 0
  processingCount.value = 0
  batchStatus.value = 'pending'
  fileStatuses.value = []
  isProcessing.value = false
  selectedFile.value = null
  // 清理localStorage
  localStorage.removeItem(BATCH_STORAGE_KEY)
}

// 组件挂载时检查是否有正在进行的批量任务
onMounted(async () => {
  const savedBatchId = localStorage.getItem(BATCH_STORAGE_KEY)
  console.log('[BatchUploader] onMounted, savedBatchId:', savedBatchId)

  if (savedBatchId) {
    try {
      // 尝试获取批量任务状态
      console.log('[BatchUploader] Fetching batch status...')
      const batch = await getBatchStatus(savedBatchId)
      console.log('[BatchUploader] Batch status:', batch?.status, 'total:', batch?.total)

      if (batch && (batch.status === 'pending' || batch.status === 'queued' || batch.status === 'processing')) {
        // 恢复任务状态
        batchId.value = savedBatchId
        updateFromBatch(batch)
        isProcessing.value = true
        // 重新开始轮询
        startPolling(savedBatchId)
        ElMessage.info('已恢复正在处理的批量任务')
      } else if (batch) {
        // 任务已完成，显示最终状态
        batchId.value = savedBatchId
        updateFromBatch(batch)
        isProcessing.value = false
        // 清理localStorage
        localStorage.removeItem(BATCH_STORAGE_KEY)
      } else {
        // 任务不存在，清理localStorage
        console.log('[BatchUploader] Batch not found, clearing localStorage')
        localStorage.removeItem(BATCH_STORAGE_KEY)
      }
    } catch (error) {
      // 获取失败，清理localStorage
      console.error('[BatchUploader] Error fetching batch:', error)
      localStorage.removeItem(BATCH_STORAGE_KEY)
    }
  }
})

// 组件卸载时停止轮询
onUnmounted(() => {
  pollController?.stop()
})
</script>

<style scoped>
.upload-area {
  border: 2px dashed var(--color-secondary-200);
  border-radius: 1rem;
  cursor: pointer;
  transition: all 0.2s ease-out;
}

.upload-area:hover {
  border-color: var(--color-primary-400);
  background-color: rgba(37, 99, 235, 0.03);
}

.upload-area-active {
  border-color: var(--color-primary-500);
  background-color: rgba(37, 99, 235, 0.05);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 条纹进度条动画 */
.progress-bar-stripe {
  background: linear-gradient(
    90deg,
    var(--color-primary-500) 0%,
    var(--color-primary-400) 50%,
    var(--color-primary-500) 100%
  );
  background-size: 200% 100%;
  animation: progress-flow 1.5s ease-in-out infinite;
}

@keyframes progress-flow {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
