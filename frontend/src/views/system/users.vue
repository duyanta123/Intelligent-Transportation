<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="用户名/姓名/手机号" clearable style="width: 240px" @keyup.enter="search" @clear="search" />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="real_name" label="姓名" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="email" label="邮箱" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.status === 1" inline-prompt active-text="启用" inactive-text="禁用" @change="toggleStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        layout="total, prev, pager, next, sizes"
        class="pager"
        @current-change="load"
        @size-change="load"
      />
    </el-card>

    <el-dialog v-model="editVisible" title="编辑用户" width="440px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="editForm.real_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchUsers, updateUser } from '@/api/auth'
import { sequenceGuard } from '@/utils/async'

const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const listSeq = sequenceGuard()
const editVisible = ref(false)
const editForm = reactive<{ id: number; username: string; real_name: string; phone: string; email: string }>({
  id: 0,
  username: '',
  real_name: '',
  phone: '',
  email: '',
})

async function load() {
  const seq = listSeq.begin()
  loading.value = true
  try {
    const { data } = await fetchUsers({ page: page.value, size: size.value, keyword: keyword.value })
    if (listSeq.isCurrent(seq)) {
      rows.value = data.list
      total.value = data.total
    }
  } finally {
    if (listSeq.isCurrent(seq)) loading.value = false
  }
}

/** 条件查询：重置到第 1 页，避免停在深层页码查不到数据 */
function search() {
  page.value = 1
  load()
}

async function toggleStatus(row: Record<string, unknown>) {
  const next = row.status === 1 ? 0 : 1
  try {
    await updateUser(row.id as number, { status: next })
    row.status = next
    ElMessage.success(next === 1 ? '已启用' : '已禁用')
  } catch {
    // 失败回显开关（http 拦截器已提示错误）
  }
}

function openEdit(row: Record<string, unknown>) {
  Object.assign(editForm, { id: row.id, username: row.username, real_name: row.real_name, phone: row.phone, email: row.email })
  editVisible.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    await updateUser(editForm.id, { real_name: editForm.real_name, phone: editForm.phone, email: editForm.email })
    ElMessage.success('保存成功')
    editVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
