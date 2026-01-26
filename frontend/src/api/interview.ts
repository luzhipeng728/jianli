import request from './request'

export interface InterviewSession {
  id: string
  token: string
  resume_id: string
  jd_id: string
  status: 'pending' | 'written_test' | 'voice' | 'completed' | 'cancelled'
  candidate_name?: string
  jd_title?: string
  written_test?: {
    score: number
    completed_at?: string
  }
  voice_interview?: {
    duration: number
    ended_at?: string
  }
  evaluation?: {
    overall_score: number
    recommendation: string
  }
  created_at: string
  started_at?: string
  completed_at?: string
}

export const createInterview = (resume_id: string, jd_id: string) =>
  request.post('/api/interview/create', { resume_id, jd_id })

export const getInterviewList = (page = 1, size = 20, status?: string) =>
  request.get('/api/interview/list', { params: { page, size, status } })

export const getInterview = (id: string) => request.get(`/api/interview/${id}`)

export const cancelInterview = (id: string, reason?: string) =>
  request.delete(`/api/interview/${id}`, { data: { reason } })

export const deleteInterview = (id: string) =>
  request.delete(`/api/interview/${id}`, { params: { permanent: true } })

export const getEvaluation = (id: string) => request.get(`/api/interview/${id}/evaluation`)
