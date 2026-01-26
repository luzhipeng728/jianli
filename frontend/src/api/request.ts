import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

// Token 存储 key
const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

// 获取 token
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY)
}

// 设置 token
export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token)
}

// 移除 token
export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// 获取用户信息
export const getUserInfo = (): { user_id: string; username: string; role: string } | null => {
  const info = localStorage.getItem(USER_KEY)
  return info ? JSON.parse(info) : null
}

// 设置用户信息
export const setUserInfo = (user: { user_id: string; username: string; role: string }): void => {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

// 检查是否已登录
export const isLoggedIn = (): boolean => {
  return !!getToken()
}

// 请求拦截器 - 添加 Authorization header
request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.detail || '请求失败'

    if (status === 401) {
      // Token 过期或无效，清除登录状态
      removeToken()
      ElMessage.error('登录已过期，请重新登录')
      // 跳转到登录页
      window.location.href = '/login'
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default request
