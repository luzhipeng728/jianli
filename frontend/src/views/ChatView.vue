<template>
  <div class="animate-fade-in h-[calc(100vh-140px)]">
    <div class="card h-full flex flex-col overflow-hidden">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-secondary-100 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <div>
            <h3 class="font-semibold text-secondary-800">AI 智能助手</h3>
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-success-500"></span>
              <span class="text-xs text-secondary-500">在线</span>
            </div>
          </div>
        </div>
        <button @click="clearChat" class="btn-secondary flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          新对话
        </button>
      </div>

      <!-- Chat Window -->
      <ChatWindow ref="chatWindowRef" class="flex-1" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'

const chatWindowRef = ref()

const clearChat = () => {
  location.reload()
}
</script>
