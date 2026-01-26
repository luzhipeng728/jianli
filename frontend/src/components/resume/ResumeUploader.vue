<template>
  <div
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
      accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png"
      @change="handleFileChange"
    />

    <div class="flex flex-col items-center gap-4 py-8">
      <!-- Upload Icon -->
      <div :class="[
        'w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300',
        isDragging ? 'bg-primary-100 scale-110' : 'bg-primary-50'
      ]">
        <svg class="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      </div>

      <!-- Text -->
      <div class="text-center">
        <p class="text-secondary-700 font-medium">
          拖拽文件到此处，或
          <span class="text-primary-600 hover:text-primary-700 cursor-pointer">点击上传</span>
        </p>
        <p class="text-sm text-secondary-400 mt-1">支持 PDF、Word、TXT、图片格式，单文件不超过10MB</p>
      </div>

      <!-- File Types Icons -->
      <div class="flex items-center gap-4 mt-2">
        <div class="flex items-center gap-1 text-xs text-secondary-400">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 2l5 5h-5V4zM6 20V4h6v6h6v10H6z"/></svg>
          PDF
        </div>
        <div class="flex items-center gap-1 text-xs text-secondary-400">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 2l5 5h-5V4zM6 20V4h6v6h6v10H6z"/></svg>
          Word
        </div>
        <div class="flex items-center gap-1 text-xs text-secondary-400">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
          图片
        </div>
      </div>
    </div>

    <!-- Loading State with Progress -->
    <div v-if="isUploading" class="absolute inset-0 bg-white/98 flex items-center justify-center rounded-xl overflow-hidden">
      <div class="flex flex-col items-center gap-4 w-full max-w-xs px-6">
        <!-- Progress Circle -->
        <div class="relative w-16 h-16">
          <svg class="w-16 h-16 transform -rotate-90">
            <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="3" fill="none" class="text-secondary-100" />
            <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="3" fill="none" class="text-primary-500"
              :stroke-dasharray="175.93" :stroke-dashoffset="175.93 * (1 - progress / 100)" stroke-linecap="round" />
          </svg>
          <div class="absolute inset-0 flex items-center justify-center">
            <span class="text-sm font-bold text-primary-600">{{ progress }}%</span>
          </div>
        </div>

        <!-- Progress Text -->
        <p class="text-sm font-medium text-secondary-700 text-center">{{ progressMessage }}</p>

        <!-- Progress Bar -->
        <div class="w-full h-1.5 bg-secondary-100 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-primary-400 to-primary-600 transition-all duration-300 ease-out rounded-full"
            :style="{ width: `${progress}%` }"></div>
        </div>
      </div>
    </div>

    <!-- LLM Output Toast (Top Right) -->
    <Teleport to="body">
      <Transition name="slide-fade">
        <div v-if="isParsing && llmOutput" class="fixed top-4 right-4 z-50 w-96 max-w-[calc(100vw-2rem)]">
          <div class="bg-white rounded-xl shadow-2xl border border-secondary-100 overflow-hidden">
            <div class="px-4 py-2 bg-primary-50 border-b border-primary-100 flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-primary-500 animate-pulse"></div>
              <span class="text-sm font-medium text-primary-700">AI 正在解析</span>
            </div>
            <div class="p-3 max-h-64 overflow-y-auto" ref="llmOutputRef">
              <pre class="text-xs text-secondary-600 whitespace-pre-wrap font-mono leading-relaxed">{{ llmOutput }}</pre>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadResumeStream } from '@/api/resume'

const emit = defineEmits(['success'])

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isUploading = ref(false)
const progress = ref(0)
const progressMessage = ref('准备上传...')
const isParsing = ref(false)
const llmOutput = ref('')
const llmOutputRef = ref<HTMLElement | null>(null)

// Auto-scroll to bottom when new content arrives
const scrollToBottom = () => {
  nextTick(() => {
    if (llmOutputRef.value) {
      llmOutputRef.value.scrollTop = llmOutputRef.value.scrollHeight
    }
  })
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    processFile(file)
  }
  target.value = ''
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) {
    processFile(file)
  }
}

const processFile = async (file: File) => {
  // Validate file size (10MB)
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过10MB')
    return
  }

  isUploading.value = true
  progress.value = 0
  progressMessage.value = '准备上传...'
  isParsing.value = false
  llmOutput.value = ''

  try {
    for await (const chunk of uploadResumeStream(file)) {
      progress.value = chunk.progress

      // 处理 LLM 流式输出
      if (chunk.type === 'llm_chunk') {
        isParsing.value = true
        llmOutput.value += chunk.content || ''
        scrollToBottom()
      } else if (chunk.message) {
        progressMessage.value = chunk.message
        if (chunk.parsing) {
          isParsing.value = true
        }
      }

      // 处理最终结果
      if (chunk.result) {
        isParsing.value = false
        if (chunk.result.status === 'success') {
          ElMessage.success('解析成功')
          emit('success', chunk.result.data)
        } else {
          ElMessage.error(chunk.result.error || '解析失败')
        }
      }
    }
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    isUploading.value = false
    isParsing.value = false
    progress.value = 0
    llmOutput.value = ''
  }
}
</script>

<style scoped>
.upload-area {
  position: relative;
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

/* Toast slide-fade transition */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
