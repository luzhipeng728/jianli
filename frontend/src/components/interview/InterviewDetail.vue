<template>
  <div class="interview-detail">
    <!-- Basic Info -->
    <div class="card p-6 mb-4">
      <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4 flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        基本信息
      </h4>
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-2">
          <p class="text-xs text-secondary-500">候选人</p>
          <p class="text-sm font-medium text-secondary-800">{{ interview.candidate_name || '-' }}</p>
        </div>
        <div class="space-y-2">
          <p class="text-xs text-secondary-500">岗位</p>
          <p class="text-sm font-medium text-secondary-800">{{ interview.jd_title || '-' }}</p>
        </div>
        <div class="space-y-2">
          <p class="text-xs text-secondary-500">状态</p>
          <span :class="['inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium', getStatusClass(interview.status)]">
            <span :class="['w-1.5 h-1.5 rounded-full', getStatusDotClass(interview.status)]"></span>
            {{ getStatusText(interview.status) }}
          </span>
        </div>
        <div class="space-y-2">
          <p class="text-xs text-secondary-500">创建时间</p>
          <p class="text-sm font-medium text-secondary-800">{{ formatDate(interview.created_at) }}</p>
        </div>
        <div class="space-y-2" v-if="interview.started_at">
          <p class="text-xs text-secondary-500">开始时间</p>
          <p class="text-sm font-medium text-secondary-800">{{ formatDate(interview.started_at) }}</p>
        </div>
        <div class="space-y-2" v-if="interview.completed_at">
          <p class="text-xs text-secondary-500">完成时间</p>
          <p class="text-sm font-medium text-secondary-800">{{ formatDate(interview.completed_at) }}</p>
        </div>
      </div>

      <!-- Interview Link -->
      <div class="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span class="text-sm font-medium text-blue-800">面试链接</span>
          </div>
          <button @click="copyLink" class="btn-secondary flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            复制链接
          </button>
        </div>
        <p class="text-xs text-blue-600 mt-2 break-all font-mono">{{ interviewUrl }}</p>
      </div>
    </div>

    <!-- Written Test Results -->
    <div v-if="interview.written_test" class="card p-6 mb-4">
      <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4 flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        笔试成绩
      </h4>
      <div class="flex items-center gap-6">
        <div class="flex-shrink-0">
          <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <div class="text-center">
              <div class="text-3xl font-bold text-white">{{ interview.written_test.score }}</div>
              <div class="text-xs text-white opacity-80">分</div>
            </div>
          </div>
        </div>
        <div class="flex-1">
          <div class="grid grid-cols-1 gap-3">
            <div class="flex items-center justify-between p-3 bg-secondary-50 rounded-lg">
              <span class="text-sm text-secondary-600">完成时间</span>
              <span class="text-sm font-medium text-secondary-800">{{ formatDate(interview.written_test.completed_at) }}</span>
            </div>
            <div class="flex items-center justify-between p-3 bg-secondary-50 rounded-lg">
              <span class="text-sm text-secondary-600">评级</span>
              <span :class="['text-sm font-semibold', getScoreClass(interview.written_test.score)]">
                {{ getScoreLevel(interview.written_test.score) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Voice Interview -->
    <div v-if="interview.voice_interview" class="card p-6 mb-4">
      <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4 flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        语音面试
      </h4>
      <div class="space-y-3">
        <div class="flex items-center justify-between p-3 bg-secondary-50 rounded-lg">
          <span class="text-sm text-secondary-600">面试时长</span>
          <span class="text-sm font-medium text-secondary-800">{{ formatDuration(interview.voice_interview.duration) }}</span>
        </div>
        <div class="flex items-center justify-between p-3 bg-secondary-50 rounded-lg">
          <span class="text-sm text-secondary-600">结束时间</span>
          <span class="text-sm font-medium text-secondary-800">{{ formatDate(interview.voice_interview.ended_at) }}</span>
        </div>
      </div>

      <!-- Conversation Replay Placeholder -->
      <div class="mt-4 p-4 border border-dashed border-secondary-300 rounded-lg bg-secondary-50">
        <div class="text-center text-secondary-500">
          <svg class="w-8 h-8 mx-auto mb-2 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p class="text-sm">对话记录回放功能即将上线</p>
        </div>
      </div>
    </div>

    <!-- Evaluation Report -->
    <div v-if="interview.evaluation" class="card p-6">
      <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4 flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
        评估报告
      </h4>

      <!-- Overall Score -->
      <div class="mb-6 p-6 bg-gradient-to-br from-primary-50 to-blue-50 rounded-xl border border-primary-100">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary-600 mb-1">综合评分</p>
            <div class="flex items-baseline gap-2">
              <span class="text-4xl font-bold text-primary-700">{{ interview.evaluation.overall_score }}</span>
              <span class="text-lg text-secondary-500">/100</span>
            </div>
          </div>
          <div class="w-20 h-20 rounded-full border-8 flex items-center justify-center" :class="getOverallScoreBorderClass(interview.evaluation.overall_score)">
            <span class="text-2xl font-bold" :class="getOverallScoreTextClass(interview.evaluation.overall_score)">
              {{ getScoreGrade(interview.evaluation.overall_score) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Recommendation -->
      <div class="p-4 bg-secondary-50 rounded-lg">
        <p class="text-xs text-secondary-500 uppercase tracking-wider mb-2">推荐结果</p>
        <p class="text-sm text-secondary-800 leading-relaxed whitespace-pre-line">{{ interview.evaluation.recommendation }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { InterviewSession } from '@/api/interview'

const props = defineProps<{
  interview: InterviewSession
}>()

const interviewUrl = computed(() => {
  const baseUrl = window.location.origin
  return `${baseUrl}/interview/${props.interview.token}`
})

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

const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (seconds?: number) => {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}分${secs}秒`
}

const getScoreLevel = (score: number) => {
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 70) return '中等'
  if (score >= 60) return '及格'
  return '不及格'
}

const getScoreClass = (score: number) => {
  if (score >= 80) return 'text-success-600'
  if (score >= 60) return 'text-warning-600'
  return 'text-danger-600'
}

const getScoreGrade = (score: number) => {
  if (score >= 90) return 'A'
  if (score >= 80) return 'B'
  if (score >= 70) return 'C'
  if (score >= 60) return 'D'
  return 'F'
}

const getOverallScoreBorderClass = (score: number) => {
  if (score >= 80) return 'border-success-500'
  if (score >= 60) return 'border-warning-500'
  return 'border-danger-500'
}

const getOverallScoreTextClass = (score: number) => {
  if (score >= 80) return 'text-success-600'
  if (score >= 60) return 'text-warning-600'
  return 'text-danger-600'
}

const copyLink = () => {
  navigator.clipboard.writeText(interviewUrl.value)
  ElMessage.success('链接已复制到剪贴板')
}
</script>

<style scoped>
.interview-detail {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
