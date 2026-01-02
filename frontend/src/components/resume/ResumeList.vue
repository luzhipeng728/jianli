<template>
  <div>
    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
        <p class="text-sm text-secondary-500">加载中...</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="resumes.length === 0" class="text-center py-12">
      <div class="w-16 h-16 rounded-2xl bg-secondary-100 flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-secondary-800 mb-1">暂无简历</h3>
      <p class="text-sm text-secondary-500">上传第一份简历开始使用</p>
    </div>

    <!-- Resume Cards -->
    <div v-else class="space-y-3">
      <div
        v-for="resume in resumes"
        :key="resume.id"
        class="card card-hover p-4 flex items-center gap-4"
      >
        <!-- Avatar -->
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0">
          <span class="text-white font-bold text-lg">{{ getInitial(resume.basic_info?.name) }}</span>
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <h4 class="font-semibold text-secondary-800 truncate">{{ resume.basic_info?.name || '未知' }}</h4>
            <span class="px-2 py-0.5 rounded text-xs bg-secondary-100 text-secondary-600">{{ resume.file_type?.toUpperCase() }}</span>
          </div>
          <div class="flex items-center gap-4 text-sm text-secondary-500">
            <span v-if="resume.basic_info?.phone" class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              {{ resume.basic_info.phone }}
            </span>
            <span class="truncate max-w-[200px]">{{ resume.file_name }}</span>
          </div>
        </div>

        <!-- Skills -->
        <div class="hidden md:flex items-center gap-1.5 flex-shrink-0">
          <span
            v-for="skill in (resume.skills?.hard_skills || []).slice(0, 3)"
            :key="skill"
            class="px-2 py-0.5 rounded-full text-xs bg-primary-50 text-primary-700"
          >
            {{ skill }}
          </span>
          <span
            v-if="(resume.skills?.hard_skills?.length || 0) > 3"
            class="px-2 py-0.5 rounded-full text-xs bg-secondary-100 text-secondary-500"
          >
            +{{ (resume.skills?.hard_skills?.length || 0) - 3 }}
          </span>
        </div>

        <!-- Warnings -->
        <div class="flex-shrink-0 w-12 text-center">
          <span
            v-if="resume.warnings?.length"
            class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-danger-50 text-danger-600 text-xs font-medium"
          >
            {{ resume.warnings.length }}
          </span>
          <span v-else class="text-secondary-300">-</span>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2 flex-shrink-0">
          <button
            @click.stop="$emit('view', resume)"
            class="p-2 rounded-lg hover:bg-primary-50 text-secondary-500 hover:text-primary-600 transition-colors"
            title="查看详情"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </button>
          <button
            @click.stop="$emit('delete', resume.id)"
            class="p-2 rounded-lg hover:bg-danger-50 text-secondary-500 hover:text-danger-600 transition-colors"
            title="删除"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResumeData } from '@/api/resume'

defineProps<{
  resumes: ResumeData[]
  loading: boolean
}>()

defineEmits(['view', 'delete'])

const getInitial = (name?: string): string => {
  return name?.charAt(0) || '?'
}
</script>

<style scoped>
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
