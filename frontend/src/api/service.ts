import http from './http'
import type { ApiResponse, PageData } from '@/types/api'

// ---------- 公告 ----------
export interface Notice {
  id: number
  title: string
  content: string
  status: number
  published_at: string | null
  created_at: string
}

export const fetchNotices = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<Notice>>>('/notices', { params })
export const createNotice = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/notices', data)
export const updateNotice = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/notices/${id}`, data)
export const deleteNotice = (id: number) => http.delete<never, ApiResponse<null>>(`/notices/${id}`)

// ---------- 投诉反馈 ----------
export interface Feedback {
  id: number
  user_id: number
  title: string
  content: string
  reply: string | null
  status: string
  status_name: string
  handled_at: string | null
  created_at: string
}

export const submitFeedback = (data: { title: string; content: string }) =>
  http.post<never, ApiResponse<{ id: number }>>('/feedback', data)
export const fetchFeedbacks = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<Feedback>>>('/feedback', { params })
export const handleFeedback = (id: number, data: { status: string; reply: string }) =>
  http.post<never, ApiResponse<Feedback>>(`/feedback/${id}/handle`, data)
