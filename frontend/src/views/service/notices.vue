<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <span class="title">公告资讯</span>
        <span class="spacer" />
        <el-button v-if="auth.role === 'admin'" type="primary" :icon="Plus" @click="openEdit()">发布公告</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="content" label="内容摘要" min-width="320" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="ellipsis">{{ stripHtml(row.content) }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="auth.role === 'admin'" label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已发布' : '草稿' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="published_at" label="发布时间" width="170">
          <template #default="{ row }">{{ row.published_at || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="auth.role === 'admin'" label="操作" width="150">
          <template #default="{ row }">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next" class="pager" @current-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑公告' : '发布公告'" width="560px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="form.content" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item v-if="!editingId" label="立即发布">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">{{ form.status === 1 || editingId ? '保存' : '存为草稿' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchNotices, createNotice, updateNotice, deleteNotice } from '@/api/service'
import type { Notice } from '@/api/service'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const rows = ref<Notice[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(0)
const form = reactive({ title: '', content: '', status: 1 })

function stripHtml(text: string) {
  return text ?? ''
}

async function load() {
  loading.value = true
  try {
    const { data } = await fetchNotices({ page: page.value, size: size.value })
    rows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openEdit(row?: Notice) {
  editingId.value = row?.id ?? 0
  Object.assign(form, row ? { title: row.title, content: row.content, status: row.status } : { title: '', content: '', status: 1 })
  dialogVisible.value = true
}

async function save() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('请填写标题与内容')
    return
  }
  if (editingId.value) {
    await updateNotice(editingId.value, { ...form })
  } else {
    await createNotice({ ...form })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await load()
}

async function remove(row: Notice) {
  await ElMessageBox.confirm(`确认删除公告「${row.title}」？`, '提示', { type: 'warning' })
  await deleteNotice(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.title {
  font-weight: 600;
}
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
