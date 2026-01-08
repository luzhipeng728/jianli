import { request } from './request'

/**
 * HR面试回放相关 API
 */
export const hrApi = {
  /**
   * 获取所有面试列表（HR后台）
   */
  listInterviews(page: number = 1, size: number = 100, status?: string) {
    return request.get('/interview/list', {
      params: { page, size, status }
    })
  },

  /**
   * 获取面试详情
   */
  getInterviewDetail(sessionId: string) {
    return request.get(`/interview/${sessionId}`)
  },

  /**
   * 获取面试评估报告
   */
  getEvaluation(sessionId: string) {
    return request.get(`/interview/${sessionId}/evaluation`)
  },

  /**
   * 获取面试对话记录
   */
  getDialogues(sessionId: string) {
    return request.get(`/interview/${sessionId}/dialogues`)
  },

  /**
   * 高亮/标记重要对话
   */
  highlightDialogue(sessionId: string, dialogueId: string, isHighlighted: boolean, notes?: string) {
    return request.post(`/interview/${sessionId}/highlight`, {
      dialogue_id: dialogueId,
      is_highlighted: isHighlighted,
      notes: notes || ''
    })
  },

  /**
   * 保存HR备注
   */
  saveNote(sessionId: string, dialogueId: string, notes: string) {
    return request.post(`/interview/${sessionId}/highlight`, {
      dialogue_id: dialogueId,
      is_highlighted: true,
      notes
    })
  }
}
