import { request } from './request'
import type {
  InterviewSession,
  WrittenQuestion,
  WrittenTestResult,
  VoiceInterviewSession,
  VoiceMessage
} from '../types'

/**
 * 面试相关 API
 */
export const interviewApi = {
  /**
   * 根据 token 获取面试会话信息
   */
  getSession(token: string) {
    return request.get<InterviewSession>(`/interview/by-token/${token}`)
  },

  /**
   * 验证面试 token
   */
  validateToken(token: string) {
    return request.post<{ valid: boolean }>('/interview/validate', { token })
  },

  /**
   * 获取笔试题目
   */
  getWrittenQuestions(token: string) {
    return request.get<WrittenQuestion[]>(`/interview/by-token/${token}/written/questions`)
  },

  /**
   * 获取流式生成笔试题目的SSE URL
   */
  getWrittenQuestionsStreamUrl(token: string) {
    return `/api/interview/by-token/${token}/written/questions/stream`
  },

  /**
   * 提交笔试答案
   */
  submitWrittenTest(token: string, result: WrittenTestResult) {
    return request.post(`/interview/${token}/written/submit`, result)
  },

  /**
   * 获取流式评估笔试答案的SSE URL（POST请求需要特殊处理）
   */
  getWrittenSubmitStreamUrl(token: string) {
    return `/api/interview/${token}/written/submit/stream`
  },

  /**
   * 开始语音面试
   */
  startVoiceInterview(token: string) {
    return request.post<VoiceInterviewSession>(`/interview/${token}/voice/start`)
  },

  /**
   * 发送语音面试消息
   */
  sendVoiceMessage(token: string, message: string) {
    return request.post<VoiceMessage>(`/interview/${token}/voice/message`, { message })
  },

  /**
   * 结束语音面试
   */
  endVoiceInterview(token: string) {
    return request.post(`/interview/${token}/voice/end`)
  },

  /**
   * 获取语音面试历史记录
   */
  getVoiceHistory(token: string) {
    return request.get<VoiceMessage[]>(`/interview/${token}/voice/history`)
  },

  /**
   * 完成整个面试流程
   */
  completeInterview(token: string) {
    return request.post(`/interview/${token}/complete`)
  }
}
