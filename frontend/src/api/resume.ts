import request, { getToken, removeToken } from './request'

export interface EducationWarning {
  risk_level: 'high' | 'medium' | 'low'
  type: string
  message: string
}

export interface DimensionScore {
  name: string
  score: number
  level: string
  highlights: string[]
  concerns: string[]
}

export interface DimensionAnalysis {
  dimensions: DimensionScore[]
  overall_score: number
  summary: string
  recommendations: string[]
  analysis_source?: string
}

export interface ResumeData {
  id: string
  file_name: string
  file_type: string
  basic_info: {
    name: string
    phone: string
    email: string
    age?: number
    gender: string
  }
  education: Array<{
    school: string
    degree: string
    major: string
    start_date?: string
    end_date?: string
    school_verified?: boolean
    school_verification_source?: string
    school_verification_message?: string
    school_level?: string
    school_department?: string
  }>
  experience: Array<{
    company: string
    title: string
    duties: string
    start_date?: string
    end_date?: string
  }>
  skills: {
    hard_skills: string[]
    soft_skills: string[]
  }
  education_warnings: EducationWarning[]  // 学历造假风险（重点）
  warnings: Array<{
    type: string
    message: string
  }>
  dimension_analysis?: DimensionAnalysis  // 多维度分析结果
  created_at: string
}

export interface UploadResult {
  status: string
  data?: ResumeData
  error?: string
}

export interface ListResult {
  data: ResumeData[]
  total: number
  page: number
  size: number
}

export const uploadResume = (file: File): Promise<UploadResult> => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/resume/upload', formData)
}

export interface UploadProgress {
  step: number
  message?: string
  progress: number
  result?: UploadResult
  type?: 'llm_chunk'
  content?: string
  parsing?: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function* uploadResumeStream(file: File): AsyncGenerator<UploadProgress> {
  const formData = new FormData()
  formData.append('file', file)

  const headers: HeadersInit = {}
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}/api/resume/upload-stream`, {
    method: 'POST',
    body: formData,
    headers,
  })

  // 处理 401 未授权错误
  if (response.status === 401) {
    removeToken()
    // 直接跳转到登录页
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

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmedLine = line.trim()
      if (trimmedLine.startsWith('data: ')) {
        try {
          const data: UploadProgress = JSON.parse(trimmedLine.slice(6))
          yield data
        } catch {
          console.warn('Failed to parse SSE data:', trimmedLine)
        }
      }
    }
  }
}

export const getResumeList = (page = 1, size = 20): Promise<ListResult> => {
  return request.get('/api/resume/list', { params: { page, size } })
}

export const getResume = (id: string) => {
  return request.get(`/api/resume/${id}`)
}

export const getResumeDetail = (id: string): Promise<ResumeData> => {
  return request.get(`/api/resume/${id}/detail`) as unknown as Promise<ResumeData>
}

export const deleteResume = (id: string) => {
  return request.delete(`/api/resume/${id}`)
}

// 批量删除简历
export interface BatchDeleteResult {
  deleted: number
  failed: number
  failed_ids: string[]
}

export const batchDeleteResumes = (ids: string[]): Promise<BatchDeleteResult> => {
  return request.post('/api/resume/batch-delete', { ids })
}

// 导出简历 - 返回下载 URL
export const getExportUrl = (format: 'json' | 'xml' | 'excel', ids?: string[]): string => {
  let url = `${API_BASE}/api/resume/export/${format}`
  if (ids && ids.length > 0) {
    url += `?ids=${ids.join(',')}`
  }
  return url
}

export const exportResumes = (format: 'json' | 'xml' | 'excel', ids?: string[]): void => {
  const url = getExportUrl(format, ids)
  window.open(url, '_blank')
}

// 岗位匹配
export interface MatchRequest {
  resume_id: string
  job_title: string
  job_description?: string
  required_skills?: string[]
  preferred_skills?: string[]
  min_experience_years?: number
  education_level?: string
  use_ai?: boolean
}

export interface MatchResult {
  overall_score: number
  skill_score: number
  experience_score: number
  education_score: number
  intention_score: number
  matched_skills: string[]
  missing_skills: string[]
  highlights: string[]
  concerns: string[]
}

export interface MatchResponse {
  resume_id: string
  job_title: string
  match_result: MatchResult
}

export const matchJob = (data: MatchRequest): Promise<MatchResponse> => {
  return request.post('/api/resume/match', data)
}

// 批量岗位匹配
export interface BatchMatchRequest {
  job_title: string
  job_description?: string
  required_skills?: string[]
  preferred_skills?: string[]
  min_experience_years?: number
  education_level?: string
  page?: number
  size?: number
  min_score?: number
}

export interface BatchMatchResultItem {
  resume_id: string
  name: string
  phone: string
  email: string
  match_score: number
  skill_score: number
  experience_score: number
  matched_skills: string[]
  missing_skills: string[]
  highlights: string[]
  concerns: string[]
}

export interface BatchMatchResponse {
  job_title: string
  total: number
  page: number
  size: number
  data: BatchMatchResultItem[]
}

export const batchMatchJob = (data: BatchMatchRequest): Promise<BatchMatchResponse> => {
  return request.post('/api/resume/batch-match', data)
}
