<template>
  <el-container class="layout">
    <!-- 侧边菜单 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo" @click="collapsed = !collapsed">
        <el-icon :size="22"><Van /></el-icon>
        <span v-if="!collapsed" class="logo-text">智慧交通平台</span>
      </div>
      <el-menu :default-active="route.path" router :collapse="collapsed" background-color="#132b45" text-color="#a7bfd6" active-text-color="#ffffff" class="side-menu">
        <template v-for="menu in auth.visibleMenus" :key="menu.id">
          <el-sub-menu v-if="menu.menu_type === 0 && menu.children?.length" :index="`m${menu.id}`">
            <template #title>
              <el-icon><component :is="menu.icon || 'Menu'" /></el-icon>
              <span>{{ menu.name }}</span>
            </template>
            <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.path">
              <el-icon><component :is="child.icon || 'Menu'" /></el-icon>
              <span>{{ child.name }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="menu.path || `/menu-${menu.id}`">
            <el-icon><component :is="menu.icon || 'Menu'" /></el-icon>
            <span>{{ menu.name }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶栏 -->
      <el-header class="header" height="56px">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>{{ route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="header-right">
          <el-tag v-if="auth.role" :type="roleTagType" size="small" effect="dark" class="role-tag">{{ roleName }}</el-tag>
          <el-dropdown @command="onCommand">
            <span class="user-name">
              <el-icon><UserFilled /></el-icon>
              {{ auth.user.real_name || auth.user.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="bigscreen">数据可视化大屏</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <!-- 修改密码弹窗 -->
  <el-dialog v-model="pwdVisible" title="修改密码" width="420px">
    <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="90px">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="pwdForm.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="pwdForm.new_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwdVisible = false">取消</el-button>
      <el-button type="primary" @click="doChangePassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { UserFilled, ArrowDown, Van } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)

const roleName = computed(() => ({ admin: '管理员', officer: '交警/运营', user: '普通用户' })[auth.role] ?? auth.role)
const roleTagType = computed(() => ({ admin: 'danger', officer: 'warning', user: 'success' })[auth.role] ?? 'info') as never

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout().then(() => router.push('/login'))
  } else if (cmd === 'bigscreen') {
    router.push('/big-screen')
  } else if (cmd === 'password') {
    pwdVisible.value = true
  }
}

// ---- 修改密码 ----
const pwdVisible = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({ old_password: '', new_password: '' })
const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
}

async function doChangePassword() {
  await pwdFormRef.value?.validate()
  await changePassword(pwdForm)
  ElMessage.success('密码修改成功，请重新登录')
  pwdVisible.value = false
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background: #132b45;
  transition: width 0.25s;
  overflow-x: hidden;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo-text {
  white-space: nowrap;
}
.side-menu {
  border-right: none;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e8ecf1;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-name {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #304156;
}
.main {
  background: #f3f6fa;
  padding: 0;
}
</style>
