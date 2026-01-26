<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <div class="card max-w-2xl w-full p-8">
      <div v-if="loading" class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p class="mt-4 text-gray-600">加载中...</p>
      </div>

      <div v-else-if="error" class="text-center">
        <div class="text-red-500 text-5xl mb-4">⚠</div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">无法访问面试</h2>
        <p class="text-gray-600">{{ error }}</p>
      </div>

      <div v-else-if="session" class="text-center">
        <h1 class="text-3xl font-bold text-gray-900 mb-6">欢迎参加面试</h1>

        <div class="text-left space-y-4 mb-8">
          <div class="flex justify-between py-3 border-b">
            <span class="text-gray-600">应聘者</span>
            <span class="font-medium">{{ session.candidate_name }}</span>
          </div>
          <div class="flex justify-between py-3 border-b">
            <span class="text-gray-600">职位</span>
            <span class="font-medium">{{ session.position }}</span>
          </div>
          <div class="flex justify-between py-3 border-b">
            <span class="text-gray-600">公司</span>
            <span class="font-medium">{{ session.company }}</span>
          </div>
        </div>

        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left">
          <h3 class="font-semibold text-blue-900 mb-2">面试流程</h3>
          <ol class="list-decimal list-inside space-y-1 text-blue-800">
            <li>笔试测评（约30分钟）</li>
            <li>AI语音面试（约20分钟）</li>
            <li>提交完成</li>
          </ol>
        </div>

        <button
          @click="startInterview"
          class="btn btn-primary w-full text-lg py-3"
          :disabled="isExpired"
        >
          {{ isExpired ? '面试已过期' : '开始面试' }}
        </button>

        <p class="text-sm text-gray-500 mt-4">
          请确保网络连接稳定，面试过程中请勿刷新页面
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { interviewApi } from '../api/interview'
import type { InterviewSession } from '../types'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const session = ref<InterviewSession | null>(null)

const token = computed(() => route.params.token as string)
const isExpired = computed(() => {
  if (!session.value) return false
  // 面试状态为已取消或已完成时视为过期
  return session.value.status === 'cancelled' || session.value.status === 'completed'
})

const loadSession = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await interviewApi.getSession(token.value)
    session.value = response.data
  } catch (err: any) {
    error.value = err.message || '加载面试信息失败'
  } finally {
    loading.value = false
  }
}

const startInterview = () => {
  router.push(`/${token.value}/written`)
}

onMounted(() => {
  loadSession()
})
</script>
