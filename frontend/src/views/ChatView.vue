<template>
  <div class="h-[calc(100vh-100px)]">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-2xl font-bold">智能问答</h1>
      <el-button @click="clearChat">新对话</el-button>
    </div>

    <el-card class="h-[calc(100%-60px)]" body-style="height: 100%; padding: 0;">
      <ChatWindow ref="chatWindowRef" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'

const chatWindowRef = ref()

const clearChat = () => {
  // 刷新页面简单实现新对话
  location.reload()
}
</script>
