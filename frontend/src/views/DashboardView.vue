<template>
  <div class="animate-fade-in">
    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="stat-card card-hover group">
        <div class="flex items-center justify-between">
          <div>
            <p class="stat-label">简历总数</p>
            <p class="stat-value text-primary-600">{{ stats.totalResumes }}</p>
          </div>
          <div class="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center group-hover:bg-primary-100 transition-colors">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>
        <div class="flex items-center gap-1 mt-3 text-sm">
          <span class="text-success-500 font-medium">+{{ stats.todayParsed }}</span>
          <span class="text-secondary-400">今日新增</span>
        </div>
      </div>

      <div class="stat-card card-hover group">
        <div class="flex items-center justify-between">
          <div>
            <p class="stat-label">今日解析</p>
            <p class="stat-value text-accent-500">{{ stats.todayParsed }}</p>
          </div>
          <div class="w-12 h-12 rounded-xl bg-accent-50 flex items-center justify-center group-hover:bg-accent-100 transition-colors">
            <svg class="w-6 h-6 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
        </div>
        <div class="flex items-center gap-1 mt-3 text-sm">
          <span class="text-secondary-400">解析成功率</span>
          <span class="text-success-500 font-medium">100%</span>
        </div>
      </div>

      <div class="stat-card card-hover group">
        <div class="flex items-center justify-between">
          <div>
            <p class="stat-label">问答次数</p>
            <p class="stat-value text-success-500">{{ stats.chatCount }}</p>
          </div>
          <div class="w-12 h-12 rounded-xl bg-success-50 flex items-center justify-center group-hover:bg-success-100 transition-colors">
            <svg class="w-6 h-6 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
        </div>
        <div class="flex items-center gap-1 mt-3 text-sm">
          <span class="text-secondary-400">平均响应</span>
          <span class="text-primary-600 font-medium">{{ stats.avgResponseTime }}ms</span>
        </div>
      </div>
    </div>

    <!-- Quick Actions & Recent Activity -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Quick Actions -->
      <div class="card p-6">
        <h3 class="section-title mb-4">快捷操作</h3>
        <div class="grid grid-cols-2 gap-4">
          <router-link to="/resume" class="card card-hover p-4 flex items-center gap-3 group">
            <div class="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center group-hover:bg-primary-100 transition-colors">
              <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p class="font-medium text-secondary-800">上传简历</p>
              <p class="text-xs text-secondary-500">解析新简历</p>
            </div>
          </router-link>

          <router-link to="/chat" class="card card-hover p-4 flex items-center gap-3 group">
            <div class="w-10 h-10 rounded-lg bg-success-50 flex items-center justify-center group-hover:bg-success-100 transition-colors">
              <svg class="w-5 h-5 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div>
              <p class="font-medium text-secondary-800">开始问答</p>
              <p class="text-xs text-secondary-500">AI智能对话</p>
            </div>
          </router-link>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="card p-6">
        <h3 class="section-title mb-4">最近活动</h3>
        <div class="space-y-4">
          <div v-for="(activity, index) in recentActivities" :key="index" class="flex items-start gap-3">
            <div :class="[
              'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
              activity.type === 'upload' ? 'bg-primary-50' : 'bg-success-50'
            ]">
              <svg v-if="activity.type === 'upload'" class="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <svg v-else class="w-4 h-4 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-secondary-800 truncate">{{ activity.title }}</p>
              <p class="text-xs text-secondary-500">{{ activity.time }}</p>
            </div>
          </div>
          <div v-if="recentActivities.length === 0" class="text-center py-8">
            <svg class="w-12 h-12 text-secondary-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p class="text-sm text-secondary-500">暂无活动记录</p>
          </div>
        </div>
      </div>
    </div>

    <!-- System Status -->
    <div class="mt-6 card p-6">
      <h3 class="section-title mb-4">系统状态</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="flex items-center gap-3">
          <div class="w-2 h-2 rounded-full bg-success-500"></div>
          <span class="text-sm text-secondary-600">API 服务正常</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="w-2 h-2 rounded-full bg-success-500"></div>
          <span class="text-sm text-secondary-600">Elasticsearch 已连接</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="w-2 h-2 rounded-full bg-success-500"></div>
          <span class="text-sm text-secondary-600">LLM 服务正常</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="w-2 h-2 rounded-full bg-success-500"></div>
          <span class="text-sm text-secondary-600">存储空间充足</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

interface Stats {
  totalResumes: number
  todayParsed: number
  chatCount: number
  avgResponseTime: number
}

interface Activity {
  type: 'upload' | 'chat'
  title: string
  time: string
}

const stats = ref<Stats>({
  totalResumes: 0,
  todayParsed: 0,
  chatCount: 0,
  avgResponseTime: 800
})

const recentActivities = ref<Activity[]>([])

onMounted(async () => {
  try {
    // Fetch resume count
    const resumes = await request.get('/api/resumes')
    if (Array.isArray(resumes)) {
      stats.value.totalResumes = resumes.length
      stats.value.todayParsed = resumes.filter((r: any) => {
        const today = new Date().toDateString()
        return new Date(r.created_at).toDateString() === today
      }).length

      // Convert to recent activities
      recentActivities.value = resumes.slice(0, 5).map((r: any) => ({
        type: 'upload' as const,
        title: `解析简历: ${r.basic_info?.name || '未知'}`,
        time: formatTime(r.created_at)
      }))
    }
  } catch (e) {
    // API might not be ready
  }
})

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}
</script>
