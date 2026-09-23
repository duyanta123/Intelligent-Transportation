import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '@/types/api'

const TOKEN_KEY = 'st_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000,
})

// 请求拦截：附加 JWT
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 并发 401 防抖：多个请求同时过期时只做一次跳转/提示
let redirectingToLogin = false

// 响应拦截：统一处理 code !== 0、401 跳登录
http.interceptors.response.use(
  (response) => {
    // blob 响应（文件下载）不走 JSON 解包，原样交还调用方
    if (response.config.responseType === 'blob') {
      return response as never
    }
    const body = response.data as ApiResponse
    if (body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body as never
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data as ApiResponse | undefined
    if (status === 401) {
      clearToken()
      if (location.pathname.startsWith('/login')) {
        ElMessage.error(body?.message || '登录已过期，请重新登录')
      } else if (!redirectingToLogin) {
        redirectingToLogin = true
        ElMessage.error(body?.message || '登录已过期，请重新登录')
        // 携带当前路径，登录后可回到原页面
        const redirect = encodeURIComponent(location.pathname + location.search)
        location.href = `/login?redirect=${redirect}`
      }
    } else if (error.response?.config?.responseType === 'blob') {
      // 错误体是 Blob 读不出 message，给导出场景一个明确提示
      ElMessage.error('导出失败，请稍后重试')
    } else {
      ElMessage.error(body?.message || '网络异常，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  },
)

export default http
