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
    <div class="flex flex-col flex-1 max-w-[90%]" :class="message.role === 'user' ? 'items-end' : 'items-start'">
      <!-- Cards FIRST (above text) -->
      <div v-if="message.cards && message.cards.length > 0" class="w-full space-y-3 mb-3">
        <template v-for="(card, idx) in message.cards" :key="idx">
          <!-- Candidates Card - Grid 3 columns -->
          <div v-if="card.type === 'candidates'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div
              v-for="(candidate, cIdx) in card.data"
              :key="cIdx"
              class="bg-white rounded-xl border border-secondary-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
              @click="handleCandidateClick(candidate)"
            >
              <div class="p-3">
                <div class="flex items-center gap-2 mb-2">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-semibold">
                    {{ candidate.name?.charAt(0) || '?' }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <h4 class="font-semibold text-secondary-900 text-sm truncate">{{ candidate.name }}</h4>
                    <p class="text-xs text-secondary-500 truncate">{{ candidate.title }}</p>
                  </div>
                  <div v-if="candidate.match_score" class="flex-shrink-0">
                    <div
                      class="px-1.5 py-0.5 rounded text-xs font-medium"
                      :class="candidate.match_score >= 80 ? 'bg-green-100 text-green-700' : candidate.match_score >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-secondary-100 text-secondary-600'"
                    >
                      {{ candidate.match_score }}%
                    </div>
                  </div>
                </div>

                <div class="text-xs text-secondary-500 mb-2 truncate">
                  <span v-if="candidate.company">{{ candidate.company }}</span>
                  <span v-if="candidate.experience_years" class="ml-2">{{ candidate.experience_years }}年经验</span>
                </div>

                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="skill in (candidate.skills || []).slice(0, 4)"
                    :key="skill"
                    class="px-1.5 py-0.5 bg-primary-50 text-primary-700 rounded text-xs"
                  >
                    {{ skill }}
                  </span>
                  <span v-if="(candidate.skills || []).length > 4" class="px-1.5 py-0.5 bg-secondary-100 text-secondary-500 rounded text-xs">
                    +{{ candidate.skills.length - 4 }}
                  </span>
                </div>

                <div v-if="candidate.highlights && candidate.highlights.length > 0" class="mt-2 pt-2 border-t border-secondary-100">
                  <p class="text-xs text-secondary-600 line-clamp-2">
                    {{ candidate.highlights[0] }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Comparison Card -->
          <div v-else-if="card.type === 'comparison'" class="bg-white rounded-xl border border-secondary-200 shadow-sm overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-secondary-50">
                  <tr>
                    <th
                      v-for="(header, hIdx) in card.data.headers"
                      :key="hIdx"
                      class="px-4 py-3 text-left font-medium text-secondary-700"
                    >
                      {{ header }}
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-secondary-100">
                  <tr v-for="(row, rIdx) in card.data.rows" :key="rIdx" class="hover:bg-secondary-50">
                    <td
                      v-for="(cell, cIdx) in row"
                      :key="cIdx"
                      class="px-4 py-3 text-secondary-800"
                      :class="cIdx === 0 ? 'font-medium' : ''"
                    >
                      {{ cell }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Stats Card -->
          <div v-else-if="card.type === 'stats'" class="bg-white rounded-xl border border-secondary-200 shadow-sm overflow-hidden">
            <div class="px-4 py-3 bg-secondary-50 border-b border-secondary-100">
              <h4 class="font-medium text-secondary-800">{{ card.data.title || '统计信息' }}</h4>
            </div>
            <div class="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div
                v-for="(item, sIdx) in card.data.items"
                :key="sIdx"
                class="text-center p-3 bg-secondary-50 rounded-lg"
              >
                <div class="text-2xl font-bold text-primary-600">{{ item.value }}</div>
                <div class="text-sm text-secondary-500 mt-1">{{ item.label }}</div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Text Content with Markdown -->
      <div
        v-if="message.content"
        class="px-4 py-3 rounded-2xl max-w-full"
        :class="message.role === 'user'
          ? 'bg-primary-600 text-white rounded-tr-sm'
          : 'bg-white border border-secondary-100 shadow-sm text-secondary-800 rounded-tl-sm'"
      >
        <div
          v-if="message.role === 'assistant'"
          class="markdown-body prose prose-slate prose-sm max-w-none
            prose-headings:font-semibold prose-headings:text-secondary-800
            prose-h3:text-base prose-h4:text-sm
            prose-p:text-secondary-700 prose-p:leading-relaxed
            prose-strong:text-secondary-900 prose-strong:font-semibold
            prose-li:text-secondary-700
            prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline
            prose-code:text-primary-700 prose-code:bg-primary-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
            prose-pre:bg-secondary-900 prose-pre:text-secondary-100
            prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5"
          v-html="renderedContent"
        ></div>
        <div v-else class="whitespace-pre-wrap leading-relaxed">{{ message.content }}</div>
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
import { computed } from 'vue'
import { marked } from 'marked'
import type { ChatMessage, StreamChunk } from '@/api/chat'

const props = defineProps<{
  message: ChatMessage
  metrics?: StreamChunk['metrics']
}>()

const emit = defineEmits<{
  candidateClick: [candidate: any]
}>()

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
})

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  try {
    return marked.parse(props.message.content) as string
  } catch {
    return props.message.content
  }
})

const handleCandidateClick = (candidate: any) => {
  emit('candidateClick', candidate)
}
</script>

<style scoped>
/* Tailwind Typography overrides for compact display */
:deep(.prose) {
  font-size: 0.9rem;
  line-height: 1.6;
}

:deep(.prose h1),
:deep(.prose h2),
:deep(.prose h3),
:deep(.prose h4) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

:deep(.prose h3) {
  font-size: 1rem;
}

:deep(.prose h4) {
  font-size: 0.95rem;
}

:deep(.prose p) {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}

:deep(.prose ul),
:deep(.prose ol) {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
  padding-left: 1.5em;
}

:deep(.prose li) {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

:deep(.prose code) {
  background-color: #f1f5f9;
  padding: 0.15em 0.4em;
  border-radius: 0.25rem;
  font-size: 0.85em;
}

:deep(.prose pre) {
  background-color: #1e293b;
  color: #e2e8f0;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0.75em 0;
}

:deep(.prose pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

:deep(.prose strong) {
  font-weight: 600;
}

/* Line clamp for highlights */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
