import request from './request'

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
  }>
  experience: Array<{
    company: string
    title: string
    duties: string
  }>
  skills: {
    hard_skills: string[]
    soft_skills: string[]
  }
  warnings: Array<{
    type: string
    message: string
  }>
  created_at: string
}

export const uploadResume = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/resume/upload', formData)
}

export const getResumeList = (page = 1, size = 20) => {
  return request.get('/api/resume/list', { params: { page, size } })
}

export const getResume = (id: string) => {
  return request.get(`/api/resume/${id}`)
}

export const deleteResume = (id: string) => {
  return request.delete(`/api/resume/${id}`)
}
