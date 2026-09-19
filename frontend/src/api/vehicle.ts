import http from './http'
import type { ApiResponse, PageData } from '@/types/api'

export interface Vehicle {
  id: number
  user_id: number | null
  plate_no: string
  vehicle_type: string
  color: string
  owner_name: string
  owner_phone: string
  created_at: string
}

export interface Violation {
  id: number
  plate_no: string
  intersection_id: number | null
  violation_type: string
  violation_time: string
  fine_amount: number
  deduct_points: number
  status: string
  status_name: string
  audit_remark: string
  remark: string
}

// ---------- 车辆 ----------
export const fetchVehicles = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<Vehicle>>>('/vehicles', { params })
export const createVehicle = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/vehicles', data)
export const updateVehicle = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/vehicles/${id}`, data)
export const deleteVehicle = (id: number) => http.delete<never, ApiResponse<null>>(`/vehicles/${id}`)

// ---------- 违章 ----------
export const fetchViolations = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<Violation>>>('/violations', { params })
export const createViolation = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/violations', data)
export const auditViolation = (id: number, data: { result: string; remark?: string }) =>
  http.post<never, ApiResponse<Violation>>(`/violations/${id}/audit`, data)
export const processViolation = (id: number) => http.post<never, ApiResponse<Violation>>(`/violations/${id}/process`)
export const fetchViolationTypes = () => http.get<never, ApiResponse<Record<string, unknown>[]>>('/violation-types')
