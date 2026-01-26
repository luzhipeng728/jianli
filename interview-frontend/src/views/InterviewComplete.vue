<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <div class="card max-w-2xl w-full p-8 text-center">
      <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
      </div>

      <h1 class="text-3xl font-bold text-gray-900 mb-4">面试已完成</h1>
      <p class="text-lg text-gray-600 mb-8">
        感谢您参加本次面试，我们会尽快审核您的面试结果并与您联系。
      </p>

      <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8 text-left">
        <h3 class="font-semibold text-blue-900 mb-3">面试总结</h3>
        <div class="space-y-2 text-blue-800">
          <div class="flex justify-between">
            <span>笔试状态</span>
            <span class="font-medium">{{ writtenStatus }}</span>
          </div>
          <div class="flex justify-between">
            <span>语音面试状态</span>
            <span class="font-medium">{{ voiceStatus }}</span>
          </div>
          <div class="flex justify-between">
            <span>总时长</span>
            <span class="font-medium">{{ totalDuration }}</span>
          </div>
          <div class="flex justify-between">
            <span>完成时间</span>
            <span class="font-medium">{{ completedTime }}</span>
          </div>
        </div>
      </div>

      <div class="space-y-3">
        <p class="text-sm text-gray-600">
          面试结果将在 3-5 个工作日内通过邮件或电话通知您
        </p>
        <p class="text-sm text-gray-500">
          如有疑问，请联系招聘部门
        </p>
      </div>

      <div class="mt-8 pt-6 border-t">
        <button
          @click="closeWindow"
          class="btn btn-secondary"
        >
          关闭窗口
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { interviewApi } from '../api/interview'
import type { InterviewSession } from '../types'

const route = useRoute()

const session = ref<InterviewSession | null>(null)
const loading = ref(true)

const token = computed(() => route.params.token as string)

const writtenStatus = computed(() => {
  return session.value?.written_test ? '已完成' : '未完成'
})

const voiceStatus = computed(() => {
  return session.value?.voice_interview ? '已完成' : '未完成'
})

const totalDuration = computed(() => {
  // 这里可以计算实际时长
  return '约 50 分钟'
})

const completedTime = computed(() => {
  const now = new Date()
  return now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
})

const loadSession = async () => {
  try {
    loading.value = true
    const response = await interviewApi.getSession(token.value)
    session.value = response.data
  } catch (err: any) {
    console.error('加载会话信息失败:', err)
  } finally {
    loading.value = false
  }
}

const closeWindow = () => {
  // 尝试关闭窗口
  window.close()

  // 如果无法关闭（某些浏览器限制），则显示提示
  setTimeout(() => {
    alert('请手动关闭此窗口')
  }, 100)
}

onMounted(async () => {
  await loadSession()

  // 标记面试完成
  try {
    await interviewApi.completeInterview(token.value)
  } catch (err: any) {
    console.error('标记完成失败:', err)
  }
})
</script>
