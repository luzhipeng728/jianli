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

    <!-- Loading State -->
    <div v-if="isUploading" class="absolute inset-0 bg-white/90 flex items-center justify-center rounded-xl">
      <div class="flex flex-col items-center gap-3">
        <div class="w-10 h-10 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
        <p class="text-sm font-medium text-secondary-600">正在解析简历...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadResume } from '@/api/resume'

const emit = defineEmits(['success'])

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isUploading = ref(false)

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

  try {
    const result = await uploadResume(file)

    if (result.status === 'success') {
      ElMessage.success('解析成功')
      emit('success', result.data)
    } else {
      ElMessage.error(result.error || '解析失败')
    }
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    isUploading.value = false
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
</style>
