import request from './request'

export interface AnalysisDimension {
  id: string
  name: string
  type: 'screening' | 'evaluation' | 'parsing'
  weight: number
  description: string
  prompt_hint: string
  is_default: boolean
  is_enabled: boolean
  created_at: string
  updated_at?: string
}

export interface DimensionCreateRequest {
  name: string
  type: 'screening' | 'evaluation' | 'parsing'
  weight?: number
  description?: string
  prompt_hint?: string
}

export interface DimensionUpdateRequest {
  name?: string
  weight?: number
  description?: string
  prompt_hint?: string
  is_enabled?: boolean
}

export const getDimensionList = (type?: string, enabledOnly = false) =>
  request.get('/api/dimension', { params: { type, enabled_only: enabledOnly } })

export const getDimension = (id: string) =>
  request.get(`/api/dimension/${id}`)

export const createDimension = (data: DimensionCreateRequest) =>
  request.post('/api/dimension', data)

export const updateDimension = (id: string, data: DimensionUpdateRequest) =>
  request.put(`/api/dimension/${id}`, data)

export const deleteDimension = (id: string) =>
  request.delete(`/api/dimension/${id}`)

export const resetDimensions = () =>
  request.post('/api/dimension/reset')

export const getScreeningConfig = () =>
  request.get('/api/dimension/config/screening')

export const getEvaluationConfig = () =>
  request.get('/api/dimension/config/evaluation')

export const getParsingConfig = () =>
  request.get('/api/dimension/config/parsing')
