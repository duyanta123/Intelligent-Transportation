import http from './http'
import type { ApiResponse, PageData } from '@/types/api'

export interface FeeRule {
  id: number
  name: string
  free_minutes: number
  first_hour_fee: number
  hourly_fee: number
  daily_cap: number
}

export interface ParkingLot {
  id: number
  name: string
  address: string
  total_slots: number
  used_slots: number
  free_slots: number
  occupancy: number
  fee_rule_id: number | null
  fee_rule_name: string
}

export interface ParkingRecord {
  id: number
  parking_lot_id: number
  parking_lot_name: string
  plate_no: string
  enter_time: string
  exit_time: string | null
  fee: number | null
  status: string
  image_url: string
}

// ---------- 停车场 ----------
export const fetchParkingLots = () => http.get<never, ApiResponse<ParkingLot[]>>('/parking-lots')
export const createParkingLot = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/parking-lots', data)
export const updateParkingLot = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/parking-lots/${id}`, data)
export const deleteParkingLot = (id: number) => http.delete<never, ApiResponse<null>>(`/parking-lots/${id}`)

// ---------- 计费规则 ----------
export const fetchFeeRules = () => http.get<never, ApiResponse<FeeRule[]>>('/fee-rules')
export const createFeeRule = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/fee-rules', data)
export const updateFeeRule = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/fee-rules/${id}`, data)
export const deleteFeeRule = (id: number) => http.delete<never, ApiResponse<null>>(`/fee-rules/${id}`)

// ---------- 出入场 ----------
export const parkingEnter = (formData: FormData) =>
  http.post<never, ApiResponse<{ record_id: number; plate_no: string; enter_time: string }>>('/parking/enter', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const parkingExit = (data: { parking_lot_id: number; plate_no: string }) =>
  http.post<never, ApiResponse<{ record_id: number; fee: number }>>('/parking/exit', data)
export const fetchParkingRecords = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<ParkingRecord>>>('/parking-records', { params })
