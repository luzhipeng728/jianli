<template>
  <div
    class="flex items-start gap-3"
    :class="message.role === 'user' ? 'flex-row-reverse' : ''"
  >
    <!-- Avatar -->
    <div
      class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
      :class="message.role === 'user' ? 'bg-primary-600' : 'bg-primary-100'"
    >
      <svg
        v-if="message.role === 'user'"
        class="w-4 h-4 text-white"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
      <svg
        v-else
        class="w-4 h-4 text-primary-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    </div>

    <!-- Message Content -->
    <div class="flex flex-col max-w-[70%]" :class="message.role === 'user' ? 'items-end' : 'items-start'">
      <div
        class="px-4 py-3 rounded-2xl"
        :class="message.role === 'user'
          ? 'bg-primary-600 text-white rounded-tr-sm'
          : 'bg-white border border-secondary-100 shadow-sm text-secondary-800 rounded-tl-sm'"
      >
        <div class="whitespace-pre-wrap leading-relaxed">{{ message.content }}</div>
      </div>

      <!-- Metrics -->
      <div
        v-if="metrics"
        class="flex items-center gap-2 mt-1.5 text-xs text-secondary-400"
      >
        <span class="flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          {{ metrics.first_token_ms }}ms
        </span>
        <span class="w-1 h-1 rounded-full bg-secondary-300"></span>
        <span class="flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ metrics.total_ms }}ms
        </span>
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
