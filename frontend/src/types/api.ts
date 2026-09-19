// 统一响应与分页类型
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface PageData<T> {
  list: T[]
  total: number
  page: number
  size: number
}

export interface MenuItem {
  id: number
  parent_id: number
  name: string
  path: string
  component: string
  icon: string
  menu_type: number
  sort_order: number
  visible: number
  children?: MenuItem[]
}

export interface UserInfo {
  id: number
  username: string
  real_name: string
  phone: string
  email: string
}

export interface LoginData {
  token: string
  expires_in: number
  role: string
  user: UserInfo
  menus: MenuItem[]
}
