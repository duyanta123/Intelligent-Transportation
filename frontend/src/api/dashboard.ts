import http from './http'
import type { ApiResponse } from '@/types/api'

export interface RealtimeData {
  flow_trend: { time: string; flow: number }[]
  map_points: { id: number; name: string; lng: number; lat: number; level: number; level_name: string; flow: number; speed: number }[]
  roads: { name: string; coords: [number, number][]; level: number; flow: number; speed: number }[]
  signal_dist: { name: string; value: number }[]
  violation_top: { name: string; value: number }[]
  parking: { name: string; total: number; used: number; rate: number }[]
  kpi: {
    today_flow: number
    avg_speed: number
    violation_today: number
    feedback_pending: number
  }
  updated_at: string
}

export const fetchRealtime = () => http.get<never, ApiResponse<RealtimeData>>('/dashboard/realtime')

export const fetchSummary = () =>
  http.get<never, ApiResponse<Record<string, unknown>>>('/dashboard/summary')

export const fetchAdminStats = () => http.get<never, ApiResponse<Record<string, number>>>('/admin/stats')
export const fetchRecentLogs = (limit = 10) =>
  http.get<never, ApiResponse<Record<string, string>[]>>('/admin/recent-logs', { params: { limit } })

// 车牌识别
export const recognizePlate = (formData: FormData) =>
  http.post<never, ApiResponse<{ plate_no: string; confidence: number }>>('/lpr/recognize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 15000,
  })

// 通用图片上传（违章取证等）
export const uploadImage = (formData: FormData) =>
  http.post<never, ApiResponse<{ url: string }>>('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
