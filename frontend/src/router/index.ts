import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 静态路由：登录页与大屏（大屏为独立全屏页，不在管理布局内）
const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/views/login/Login.vue'), meta: { title: '登录' } },
  {
    path: '/big-screen',
    name: 'bigScreen',
    component: () => import('@/views/bigscreen/index.vue'),
    meta: { title: '数据可视化大屏', standalone: true },
  },
  {
    path: '/',
    component: () => import('@/views/layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '系统仪表盘' } },
      { path: 'traffic/intersections', name: 'intersections', component: () => import('@/views/traffic/intersections.vue'), meta: { title: '路口管理' } },
      { path: 'traffic/signal-plans', name: 'signalPlans', component: () => import('@/views/traffic/signal-plans.vue'), meta: { title: '信号配时' } },
      { path: 'traffic/sections', name: 'sections', component: () => import('@/views/traffic/sections.vue'), meta: { title: '路段管理' } },
      { path: 'traffic/flow', name: 'flow', component: () => import('@/views/traffic/flow.vue'), meta: { title: '流量与拥堵' } },
      { path: 'vehicle/vehicles', name: 'vehicles', component: () => import('@/views/vehicle/vehicles.vue'), meta: { title: '车辆管理' } },
      { path: 'vehicle/violations', name: 'violations', component: () => import('@/views/vehicle/violations.vue'), meta: { title: '违章管理' } },
      { path: 'parking/lots', name: 'parkingLots', component: () => import('@/views/parking/lots.vue'), meta: { title: '停车场管理' } },
      { path: 'parking/records', name: 'parkingRecords', component: () => import('@/views/parking/records.vue'), meta: { title: '出入场记录' } },
      { path: 'parking/fee-rules', name: 'feeRules', component: () => import('@/views/parking/fee-rules.vue'), meta: { title: '计费规则' } },
      { path: 'tools/lpr', name: 'lpr', component: () => import('@/views/tools/lpr.vue'), meta: { title: '车牌识别' } },
      { path: 'service/notices', name: 'notices', component: () => import('@/views/service/notices.vue'), meta: { title: '公告资讯' } },
      { path: 'service/feedback', name: 'feedback', component: () => import('@/views/service/feedback.vue'), meta: { title: '投诉反馈' } },
      { path: 'system/users', name: 'users', component: () => import('@/views/system/users.vue'), meta: { title: '用户管理' } },
      { path: 'system/roles', name: 'roles', component: () => import('@/views/system/roles.vue'), meta: { title: '角色管理' } },
      { path: 'system/menus', name: 'menus', component: () => import('@/views/system/menus.vue'), meta: { title: '菜单管理' } },
      { path: 'system/logs', name: 'logs', component: () => import('@/views/system/logs.vue'), meta: { title: '操作日志' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  document.title = to.meta.title ? `${to.meta.title} - 智慧交通综合管理服务平台` : '智慧交通综合管理服务平台'
  if (to.path === '/login' || to.meta.standalone) {
    return true
  }
  if (!auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
