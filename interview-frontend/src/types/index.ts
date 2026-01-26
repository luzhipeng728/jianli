// 面试会话信息
export interface InterviewSession {
  id: string
  token: string
  resume_id: string
  jd_id: string
  candidate_name: string
  position: string
  company: string
  resume_summary?: string  // 简历摘要（用于AI面试官）
  job_info?: string        // 岗位信息（用于AI面试官）
  written_test_summary?: string  // 笔试摘要（用于AI面试官开场）
  status: 'pending' | 'written_test' | 'voice' | 'completed' | 'cancelled'
  written_test?: any
  voice_interview?: any
  evaluation?: any
  created_at: string
  started_at?: string
  completed_at?: string
  cancelled_at?: string
  cancelled_reason?: string
}

// 笔试题目
export interface WrittenQuestion {
  id: string
  type: 'single' | 'single_choice' | 'multiple' | 'multiple_choice' | 'judgment' | 'text'
  question?: string
  content?: string
  options?: string[]
  correctAnswer?: string | string[]
  score?: number
  points?: number
}

// 笔试答案
export interface WrittenAnswer {
  questionId: string
  answer: string | string[]
}

// 笔试结果
export interface WrittenTestResult {
  sessionId: string
  answers: WrittenAnswer[]
  score?: number
  totalScore?: number
  submittedAt: string
}

// 语音面试消息
export interface VoiceMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  audioUrl?: string
}

// 语音面试会话
export interface VoiceInterviewSession {
  sessionId: string
  status: 'active' | 'paused' | 'completed'
  messages: VoiceMessage[]
  duration: number
  startedAt: string
  endedAt?: string
}

// API 响应
export interface ApiResponse<T = any> {
  status?: string
  success?: boolean
  code?: number
  message?: string
  detail?: string
  data: T
}

// API 错误
export interface ApiError {
  code: number
  message: string
  details?: any
}
