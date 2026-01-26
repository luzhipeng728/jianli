import request from './request'
import { setToken, setUserInfo, removeToken, getToken, getUserInfo, isLoggedIn } from './request'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: {
    user_id: string
    username: string
    role: string
  }
}

export interface UserInfo {
  user_id: string
  username: string
  role: string
}

// 登录
export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const response = await request.post<any, LoginResponse>('/api/auth/login', data)
  // 保存 token 和用户信息
  setToken(response.access_token)
  setUserInfo(response.user)
  return response
}

// 登出
export const logout = (): void => {
  removeToken()
}

// 获取当前用户信息
export const getCurrentUser = (): Promise<UserInfo> => {
  return request.get('/api/auth/me')
}

// 刷新 token
export const refreshToken = (): Promise<{ access_token: string; token_type: string }> => {
  return request.post('/api/auth/refresh')
}

// 导出工具函数
export { getToken, getUserInfo, isLoggedIn, removeToken }
