<template>
  <div class="flex h-screen bg-secondary-50">
    <!-- Modern Sidebar -->
    <aside class="w-64 bg-white border-r border-secondary-100 flex flex-col">
      <!-- Logo Area -->
      <div class="p-6 border-b border-secondary-100">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 class="text-lg font-bold text-secondary-900 font-heading">智能简历</h1>
            <p class="text-xs text-secondary-500">AI Resume Assistant</p>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          custom
          v-slot="{ isActive, navigate }"
        >
          <div
            @click="navigate"
            :class="[
              'sidebar-item',
              isActive ? 'sidebar-item-active' : ''
            ]"
          >
            <component :is="item.icon" class="w-5 h-5" />
            <span>{{ item.title }}</span>
          </div>
        </router-link>
      </nav>

      <!-- Footer -->
      <div class="p-4 border-t border-secondary-100">
        <div class="flex items-center gap-3 px-4 py-3">
          <div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
            <svg class="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-secondary-900 truncate">管理员</p>
            <p class="text-xs text-secondary-500 truncate">admin@example.com</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-auto">
      <!-- Top Bar -->
      <header class="sticky top-0 z-10 bg-white/80 backdrop-blur-sm border-b border-secondary-100 px-8 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="page-title">{{ currentPageTitle }}</h2>
            <p class="text-sm text-secondary-500 mt-0.5">{{ currentPageDescription }}</p>
          </div>
          <div class="flex items-center gap-3">
            <button class="btn-secondary flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              刷新
            </button>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <div class="p-8">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, h } from 'vue'
import { useRoute } from 'vue-router'

// SVG Icon Components
const HomeIcon = markRaw({
  render() {
    return h('svg', { class: 'w-5 h-5', fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' })
    ])
  }
})

const DocumentIcon = markRaw({
  render() {
    return h('svg', { class: 'w-5 h-5', fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' })
    ])
  }
})

const ChatIcon = markRaw({
  render() {
    return h('svg', { class: 'w-5 h-5', fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' })
    ])
  }
})

const route = useRoute()

const menuItems = [
  { path: '/', title: '仪表盘', icon: HomeIcon },
  { path: '/resume', title: '简历解析', icon: DocumentIcon },
  { path: '/chat', title: '智能问答', icon: ChatIcon },
]

const pageInfo: Record<string, { title: string; description: string }> = {
  '/': { title: '仪表盘', description: '查看系统概览和统计数据' },
  '/resume': { title: '简历解析', description: '上传并解析简历文件' },
  '/chat': { title: '智能问答', description: '与AI助手进行对话' },
}

const currentPageTitle = computed(() => pageInfo[route.path]?.title || '页面')
const currentPageDescription = computed(() => pageInfo[route.path]?.description || '')
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
