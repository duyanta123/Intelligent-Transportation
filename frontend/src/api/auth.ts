import http from './http'
import type { ApiResponse, LoginData, PageData, UserInfo, MenuItem } from '@/types/api'

// ---------- 认证 ----------
export const fetchCaptcha = () => http.get<never, ApiResponse<{ key: string; image: string }>>('/auth/captcha')
export const login = (data: { username: string; password: string; captcha_key: string; captcha_code: string }) =>
  http.post<never, ApiResponse<LoginData>>('/auth/login', data)
export const register = (data: { username: string; password: string; real_name?: string; phone?: string }) =>
  http.post<never, ApiResponse<{ id: number }>>('/auth/register', data)
export const logout = () => http.post<never, ApiResponse<null>>('/auth/logout')
export const changePassword = (data: { old_password: string; new_password: string }) =>
  http.put<never, ApiResponse<null>>('/auth/password', data)
export const fetchProfile = () =>
  http.get<never, ApiResponse<UserInfo & { role: string; menus: MenuItem[] }>>('/auth/profile')

// ---------- 用户/角色/菜单/日志 ----------
export const fetchUsers = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<UserInfo & { status: number; created_at: string }>>>('/users', { params })
export const updateUser = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/users/${id}`, data)
export const fetchRoles = () => http.get<never, ApiResponse<{ id: number; code: string; name: string }[]>>('/roles')
export const fetchMenus = () => http.get<never, ApiResponse<MenuItem[]>>('/menus')
export const createMenu = (data: Record<string, unknown>) => http.post<never, ApiResponse<{ id: number }>>('/menus', data)
export const updateMenu = (id: number, data: Record<string, unknown>) => http.put<never, ApiResponse<null>>(`/menus/${id}`, data)
export const deleteMenu = (id: number) => http.delete<never, ApiResponse<null>>(`/menus/${id}`)
export const fetchOpLogs = (params: Record<string, unknown>) =>
  http.get<never, ApiResponse<PageData<Record<string, string>>>>('/op-logs', { params })
