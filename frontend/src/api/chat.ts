export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface StreamChunk {
  type: 'thinking' | 'text' | 'card' | 'done' | 'error'
  content?: string
  card_type?: string
  data?: any
  metrics?: {
    first_token_ms: number
    total_ms: number
    session_id: string
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function* chatStream(
  message: string,
  sessionId?: string,
  showThinking = false
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE}/api/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      show_thinking: showThinking,
    }),
  })

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) return

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const chunk: StreamChunk = JSON.parse(line.slice(6))
          yield chunk
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}
