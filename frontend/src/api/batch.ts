/**
 * 批量简历处理API - 后台异步处理模式
 */
import request from './request'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const WS_BASE = API_BASE.replace(/^http/, 'ws') || `ws://${window.location.host}`

export interface ResumeWarning {
  type: string
  message: string
}

export interface FileInfo {
  file_id: string
  file_name: string
  status: 'pending' | 'queued' | 'processing' | 'success' | 'failed' | 'retrying'
  status_detail?: string  // 详细状态：读取文件、提取文本、OCR识别、LLM解析中、创建向量、保存数据
  progress: number
  error?: string
  result?: {
    resume_id: string
    name: string
    phone?: string
    email?: string
    skills?: string[]
    warnings_count?: number
    warnings?: ResumeWarning[]
  }
  llm_output?: string
  retry_count: number
  updated_at: string
}

export interface BatchTask {
  batch_id: string
  status: string
  total: number
  completed: number
  failed: number
  progress: number
  processing?: number
  files: FileInfo[]
  created_at: string
  updated_at: string
}

export interface BatchSummary {
  batch_id: string
  status: string
  total: number
  completed: number
  failed: number
  progress: number
  created_at: string
  updated_at: string
}

export interface BatchListResponse {
  total: number
  batches: BatchSummary[]
}

export interface BatchCreateResponse {
  batch_id: string
  total_files: number
  status: string
  files: { file_id: string; file_name: string }[]
  message: string
  skipped?: { file: string; reason: string }[]  // 跳过的无效文件
}

export interface BatchWSMessage {
  type: 'connected' | 'update' | 'completed' | 'deleted' | 'error'
  batch_id?: string
  status?: string
  total?: number
  completed?: number
  failed?: number
  progress?: number
  processing?: number
  files?: FileInfo[]
  success?: number
  error?: string
  updated_at?: string
}

/**
 * 创建批量上传任务（上传后自动开始后台处理）
 */
export async function createBatchTask(files: File[]): Promise<BatchCreateResponse> {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })

  const data = await request.post('/api/batch/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return data as unknown as BatchCreateResponse
}

/**
 * 获取所有批量任务列表
 */
export async function getBatchList(): Promise<BatchListResponse> {
  const data = await request.get('/api/batch/list')
  return data as unknown as BatchListResponse
}

/**
 * 获取批量任务详细状态
 */
export async function getBatchStatus(batchId: string): Promise<BatchTask> {
  const data = await request.get(`/api/batch/status/${batchId}`)
  return data as unknown as BatchTask
}

/**
 * 重试失败的文件
 */
export async function retryFailed(batchId: string, fileId?: string): Promise<{ message: string }> {
  const params = fileId ? `?file_id=${fileId}` : ''
  const data = await request.post(`/api/batch/retry/${batchId}${params}`)
  return data as unknown as { message: string }
}

/**
 * 删除批量任务
 */
export async function deleteBatch(batchId: string): Promise<void> {
  await request.delete(`/api/batch/${batchId}`)
}

/**
 * 轮询获取批量任务状态
 */
export function pollBatchStatus(
  batchId: string,
  onUpdate: (batch: BatchTask) => void,
  interval: number = 2000
): { stop: () => void } {
  let running = true
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const poll = async () => {
    if (!running) return

    try {
      const batch = await getBatchStatus(batchId)
      onUpdate(batch)

      // 如果任务完成，停止轮询
      if (batch.status === 'success' || batch.status === 'failed') {
        running = false
        return
      }

      // 根据处理状态动态调整轮询间隔
      // 有文件正在处理时，加快轮询（1秒）
      const hasProcessing = batch.files.some(f => f.status === 'processing')
      const nextInterval = hasProcessing ? 1000 : interval

      if (running) {
        timeoutId = setTimeout(poll, nextInterval)
      }
    } catch (e) {
      console.error('轮询失败:', e)
      // 出错时也要继续轮询
      if (running) {
        timeoutId = setTimeout(poll, interval)
      }
    }
  }

  poll()

  return {
    stop: () => {
      running = false
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }
}

/**
 * WebSocket连接获取实时进度
 */
export function connectBatchWebSocket(
  batchId: string,
  onMessage: (msg: BatchWSMessage) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): { close: () => void } {
  const wsUrl = `${WS_BASE}/api/batch/ws/${batchId}`
  const ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('WebSocket消息解析失败:', e)
    }
  }

  ws.onerror = (event) => {
    console.error('WebSocket错误:', event)
    onError?.(event)
  }

  ws.onclose = () => {
    onClose?.()
  }

  return {
    close: () => {
      ws.close()
    }
  }
}

/**
 * 自动选择最佳连接方式（优先WebSocket，降级到轮询）
 */
export function watchBatchProgress(
  batchId: string,
  onUpdate: (batch: BatchTask | null, type: 'update' | 'completed' | 'error') => void,
  options: {
    preferWebSocket?: boolean
    pollInterval?: number
  } = {}
): { stop: () => void } {
  const { preferWebSocket = true, pollInterval = 2000 } = options
  let wsConnection: { close: () => void } | null = null
  let pollConnection: { stop: () => void } | null = null
  let stopped = false

  const usePolling = () => {
    if (stopped) return
    pollConnection = pollBatchStatus(batchId, (batch) => {
      onUpdate(batch, batch.status === 'success' || batch.status === 'failed' ? 'completed' : 'update')
    }, pollInterval)
  }

  if (preferWebSocket) {
    try {
      wsConnection = connectBatchWebSocket(
        batchId,
        (msg) => {
          if (msg.type === 'update') {
            onUpdate(msg as unknown as BatchTask, 'update')
          } else if (msg.type === 'completed') {
            onUpdate(msg as unknown as BatchTask, 'completed')
          } else if (msg.type === 'error' || msg.type === 'deleted') {
            onUpdate(null, 'error')
          }
        },
        () => {
          // WebSocket错误，降级到轮询
          console.log('WebSocket连接失败，降级到轮询模式')
          wsConnection = null
          usePolling()
        },
        () => {
          // WebSocket关闭
          wsConnection = null
        }
      )
    } catch {
      // WebSocket不可用，使用轮询
      usePolling()
    }
  } else {
    usePolling()
  }

  return {
    stop: () => {
      stopped = true
      wsConnection?.close()
      pollConnection?.stop()
    }
  }
}
