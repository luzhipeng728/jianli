export interface CardData {
  type: 'candidates' | 'comparison' | 'stats'
  data: any
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  cards?: CardData[]
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

// 从 localStorage 获取 token
const getToken = (): string | null => {
  return localStorage.getItem('access_token')
}

// 清除 token
const removeToken = (): void => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_info')
}

export async function* chatStream(
  message: string,
  sessionId?: string,
  showThinking = false,
  jdId?: string
): AsyncGenerator<StreamChunk> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
    'Cache-Control': 'no-cache',
  }

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}/api/chat/message`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      session_id: sessionId,
      show_thinking: showThinking,
      jd_id: jdId || undefined,
    }),
  })

  // 处理 401 未授权错误
  if (response.status === 401) {
    removeToken()
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    // 将新数据追加到缓冲区
    buffer += decoder.decode(value, { stream: true })

    // 按行分割处理
    const lines = buffer.split('\n')
    // 保留最后一行（可能不完整）
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmedLine = line.trim()
      if (trimmedLine.startsWith('data: ')) {
        try {
          const chunk: StreamChunk = JSON.parse(trimmedLine.slice(6))
          yield chunk
        } catch (e) {
          // 忽略解析错误
          console.warn('Failed to parse SSE data:', trimmedLine)
        }
      }
    }
  }

  // 处理缓冲区中剩余的数据
  if (buffer.trim().startsWith('data: ')) {
    try {
      const chunk: StreamChunk = JSON.parse(buffer.trim().slice(6))
      yield chunk
    } catch (e) {
      // 忽略
    }
  }
}
