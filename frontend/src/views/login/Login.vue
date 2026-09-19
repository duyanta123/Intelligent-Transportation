<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1 class="title">智慧交通综合管理服务平台</h1>
      <p class="subtitle">Smart Traffic Management &amp; Service Platform</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" size="large" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="captcha_code">
          <div class="captcha-row">
            <el-input v-model="form.captcha_code" placeholder="验证码" :prefix-icon="Key" maxlength="4" />
            <img v-if="captcha.image" :src="captcha.image" class="captcha-img" title="点击刷新验证码" alt="验证码" @click="refreshCaptcha" />
          </div>
        </el-form-item>
        <el-button type="primary" class="login-btn" size="large" :loading="loading" @click="submit">登 录</el-button>
        <el-button class="login-btn" size="large" @click="registerVisible = true">注册账号</el-button>
      </el-form>
      <el-alert class="tips" type="info" :closable="false" title="测试账号：admin / officer / user，密码均为 123456" />
    </div>

    <el-dialog v-model="registerVisible" title="注册账号" width="420px">
      <el-form ref="regFormRef" :model="regForm" :rules="regRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="regForm.username" placeholder="3-32 位字母数字下划线" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="regForm.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="regForm.real_name" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="regForm.phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerVisible = false">取消</el-button>
        <el-button type="primary" :loading="regLoading" @click="doRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Key } from '@element-plus/icons-vue'
import { fetchCaptcha, register } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '', captcha_key: '', captcha_code: '' })

const captcha = ref({ key: '', image: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function refreshCaptcha() {
  const { data } = await fetchCaptcha()
  captcha.value = data
  form.captcha_key = data.key
  form.captcha_code = ''
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await auth.login({ ...form })
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } finally {
    loading.value = false
    await refreshCaptcha()
  }
}

// ---- 注册 ----
const registerVisible = ref(false)
const regLoading = ref(false)
const regFormRef = ref<FormInstance>()
const regForm = reactive({ username: '', password: '', real_name: '', phone: '' })
const regRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]{3,32}$/, message: '3-32 位字母数字下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
}

async function doRegister() {
  await regFormRef.value?.validate()
  regLoading.value = true
  try {
    await register({ ...regForm })
    ElMessage.success('注册成功，请登录')
    registerVisible.value = false
    form.username = regForm.username
    await refreshCaptcha()
  } finally {
    regLoading.value = false
  }
}

onMounted(refreshCaptcha)
</script>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1b3a5c 0%, #2f6fa7 55%, #56b8e6 100%);
}
.login-card {
  width: 400px;
  padding: 36px 40px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 18px 50px rgba(0, 30, 60, 0.35);
}
.title {
  margin: 0 0 4px;
  font-size: 20px;
  color: #16324f;
  text-align: center;
}
.subtitle {
  margin: 0 0 22px;
  font-size: 12px;
  color: #8a9bb0;
  text-align: center;
}
.captcha-row {
  display: flex;
  gap: 10px;
  width: 100%;
}
.captcha-img {
  height: 40px;
  width: 130px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #dcdfe6;
}
.login-btn {
  width: 100%;
  margin: 6px 0 0;
}
.tips {
  margin-top: 14px;
}
</style>
