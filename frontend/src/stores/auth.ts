import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, logout as logoutApi } from '@/api/auth'
import { setToken, clearToken, getToken } from '@/api/http'
import type { MenuItem, LoginData } from '@/types/api'

const USER_KEY = 'st_user'
const MENUS_KEY = 'st_menus'
const ROLE_KEY = 'st_role'

function loadJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref(loadJSON<{ id: number; username: string; real_name: string }>(USER_KEY, { id: 0, username: '', real_name: '' }))
  const role = ref(localStorage.getItem(ROLE_KEY) ?? '')
  const menus = ref<MenuItem[]>(loadJSON<MenuItem[]>(MENUS_KEY, []))

  const isLoggedIn = computed(() => !!token.value)
  /** 侧边栏可见菜单：过滤隐藏目录 */
  const visibleMenus = computed(() => menus.value)

  async function login(payload: { username: string; password: string; captcha_key: string; captcha_code: string }) {
    const data: LoginData = (await loginApi(payload)).data
    token.value = data.token
    user.value = data.user
    role.value = data.role
    menus.value = data.menus
    setToken(data.token)
    localStorage.setItem(ROLE_KEY, data.role)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    localStorage.setItem(MENUS_KEY, JSON.stringify(data.menus))
    return data
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 后端不可达时也要清理本地状态
    }
    reset()
  }

  function reset() {
    token.value = ''
    user.value = { id: 0, username: '', real_name: '' }
    role.value = ''
    menus.value = []
    clearToken()
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(MENUS_KEY)
  }

  return { token, user, role, menus, isLoggedIn, visibleMenus, login, logout, reset }
})
