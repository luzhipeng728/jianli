import request from './request'

export interface InterviewConfig {
  written_question_count: number
  voice_max_duration: number
  focus_areas: string[]
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface JobDescription {
  id: string
  title: string
  department: string
  description: string
  requirements: string[]
  required_skills: string[]
  preferred_skills: string[]
  interview_config: InterviewConfig
  created_at: string
  updated_at?: string
}

export interface JDListResult {
  data: JobDescription[]
  total: number
  page: number
  size: number
}

export interface RecommendedResume {
  resume_id: string
  name: string
  phone: string
  email: string
  match_score: number
  matched_skills: string[]
  education: string
  latest_company: string
  latest_title: string
  created_at: string
}

export interface JDResumesResult {
  jd_id: string
  jd_title: string
  total: number
  page: number
  size: number
  data: RecommendedResume[]
}

export const createJD = (data: Partial<JobDescription>) => request.post('/api/jd', data)
export const getJDList = (page = 1, size = 20): Promise<JDListResult> => request.get('/api/jd', { params: { page, size } })
export const getJD = (id: string): Promise<JobDescription> => request.get(`/api/jd/${id}`)
export const updateJD = (id: string, data: Partial<JobDescription>) => request.put(`/api/jd/${id}`, data)
export const deleteJD = (id: string) => request.delete(`/api/jd/${id}`)
export const getJDResumes = (id: string, page = 1, size = 20, minScore = 0): Promise<JDResumesResult> =>
  request.get(`/api/jd/${id}/resumes`, { params: { page, size, min_score: minScore } })

// AI Screening API
export interface ScreeningResumeTask {
  resume_id: string
  resume_name: string
  status: 'pending' | 'queued' | 'processing' | 'success' | 'failed'
  status_detail?: string  // 详细状态：读取简历、AI评分中、保存结果
  progress: number
  match_score?: number
  skill_score?: number
  experience_score?: number
  education_score?: number
  matched_skills?: string[]
  error?: string
  updated_at: string
}

export interface ScreeningStatusResult {
  batch_id?: string
  jd_id: string
  jd_title?: string
  status: string
  total?: number
  completed?: number
  failed?: number
  skipped?: number
  processing?: number
  progress?: number
  resumes?: ScreeningResumeTask[]
  analyzed_count?: number
  has_results?: boolean
  message?: string
  created_at?: string
  updated_at?: string
}

export interface ScreeningResult {
  resume_id: string
  name: string
  phone: string
  email: string
  match_score: number
  skill_score: number
  experience_score: number
  education_score: number
  matched_skills: string[]
  missing_skills: string[]
  highlights: string[]
  concerns: string[]
  education: string
  latest_company: string
  latest_title: string
  analyzed_at: string
}

export interface ScreeningResultsResponse {
  jd_id: string
  jd_title: string
  total: number
  page: number
  size: number
  data: ScreeningResult[]
}

export interface StartScreeningResult {
  batch_id: string
  status: string
  message: string
  total: number
  completed: number
  skipped?: number
  progress: number
}

export const startScreening = (jdId: string, minScore = 0): Promise<StartScreeningResult> =>
  request.post(`/api/jd/${jdId}/screen`, { min_score: minScore })

export const getScreeningStatus = (jdId: string, batchId?: string): Promise<ScreeningStatusResult> =>
  request.get(`/api/jd/${jdId}/screen/status`, { params: batchId ? { batch_id: batchId } : {} })

export const getScreeningResults = (jdId: string, page = 1, size = 20, minScore = 0): Promise<ScreeningResultsResponse> =>
  request.get(`/api/jd/${jdId}/screen/results`, { params: { page, size, min_score: minScore } })
