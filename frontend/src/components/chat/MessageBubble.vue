<template>
  <div
    class="flex mb-4"
    :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[70%] px-4 py-2 rounded-lg"
      :class="message.role === 'user'
        ? 'bg-primary text-white'
        : 'bg-white border shadow-sm'"
    >
      <div class="whitespace-pre-wrap">{{ message.content }}</div>
      <div
        v-if="metrics"
        class="text-xs mt-1 opacity-60"
      >
        首字 {{ metrics.first_token_ms }}ms / 总计 {{ metrics.total_ms }}ms
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage, StreamChunk } from '@/api/chat'

defineProps<{
  message: ChatMessage
  metrics?: StreamChunk['metrics']
}>()
</script>
