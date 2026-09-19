import http from './http'
import type { ApiResponse, PageData } from '@/types/api'

export interface Intersection {
  id: number
  name: string
  longitude: number
  latitude: number
  lane_count: number
  district: string
  status: number
}

export interface SignalPlan {
  id: number
  intersection_id: number
  intersection_name: string
  name: string
  mode: string
  cycle_seconds: number
  phase_count: number
  phases: { name: string; green: number; yellow: number; allRed: number }[]
  green_ratio: number
  is_active: number
}

export interface RoadSection {
  id: number
  name: string
  start_intersection_id: number
  end_intersection_id: number
  start_name: string
  end_name: string
  lane_count: number
  length_km: number
  direction: string
  capacity: number
}

// ---------- 路口 ----------
export const fetchIntersections = (params?: Record<string, unknown>) =>
  http.get<never, ApiResponse<Intersection[]>>('/intersections', { params })
export const createIntersection = (data: Record<string, unknown>) =>
  http.post<never, ApiResponse<{ id: number }>>('/intersections', data)
export const updateIntersection = (id: number, data: Record<string, unknown>) =>
  http.put<never, ApiResponse<null>>(`/intersections/${id}`, data)
export const deleteIntersection = (id: number) => http.delete<never, ApiResponse<null>>(`/intersections/${id}`)

// ---------- 信号配时 ----------
export const fetchSignalPlans = (params?: Record<string, unknown>) =>
  http.get<never, ApiResponse<SignalPlan[]>>('/signal-plans', { params })
export const createSignalPlan = (data: Record<string, unknown>) =>
  http.post<never, ApiResponse<{ id: number }>>('/signal-plans', data)
export const updateSignalPlan = (id: number, data: Record<string, unknown>) =>
  http.put<never, ApiResponse<null>>(`/signal-plans/${id}`, data)
export const deleteSignalPlan = (id: number) => http.delete<never, ApiResponse<null>>(`/signal-plans/${id}`)
export const calcWebster = (phases: { name: string; flow: number; lanes: number }[]) =>
  http.post<never, ApiResponse<{ cycle_seconds: number; total_lost: number; y_sum: number; oversaturated: boolean; phases: { name: string; green: number; y: number }[] }>>(
    '/signal-plans/calc',
    { phases },
  )
export const fetchSignalStatus = () => http.get<never, ApiResponse<Record<string, unknown>[]>>('/signal-status')

// ---------- 路况 ----------
export const fetchSections = (params?: Record<string, unknown>) =>
  http.get<never, ApiResponse<RoadSection[]>>('/road-sections', { params })
export const createSection = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/road-sections', data)
export const updateSection = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/road-sections/${id}`, data)
export const deleteSection = (id: number) => http.delete<never, ApiResponse<null>>(`/road-sections/${id}`)
export const reportFlow = (data: { road_section_id: number; flow: number; speed?: number }) =>
  http.post<never, ApiResponse<Record<string, number>>>('/traffic-flow/report', data)
export const fetchFlowHistory = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<{ time: string; avg_flow: number; max_flow: number; avg_speed: number; samples: number }>>>(
    '/traffic-flow/history',
    { params },
  )
export const fetchCongestion = () =>
  http.get<never, ApiResponse<{ sections: Record<string, unknown>[]; intersections: Record<string, unknown>[] }>>(
    '/traffic-flow/congestion',
  )
