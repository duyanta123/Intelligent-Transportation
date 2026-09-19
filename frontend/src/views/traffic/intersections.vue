<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="路口名称" clearable style="width: 200px" @keyup.enter="load" />
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <span class="spacer" />
        <el-button v-if="auth.role === 'admin'" type="primary" :icon="Plus" @click="openEdit()">新增路口</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="路口名称" min-width="130" />
        <el-table-column prop="longitude" label="经度" width="110" />
        <el-table-column prop="latitude" label="纬度" width="110" />
        <el-table-column prop="lane_count" label="车道数" width="90" />
        <el-table-column prop="district" label="辖区" width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="auth.role !== 'user'" label="操作" width="170">
          <template #default="{ row }">
            <el-button v-if="auth.role === 'admin'" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="auth.role === 'admin'" text type="danger" @click="remove(row)">删除</el-button>
            <el-button text type="success" @click="goCalc(row)">配时计算</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑路口' : '新增路口'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：中山路口" />
        </el-form-item>
        <el-form-item label="经度" prop="longitude">
          <el-input-number v-model="form.longitude" :precision="6" :step="0.001" :min="-180" :max="180" style="width: 100%" />
        </el-form-item>
        <el-form-item label="纬度" prop="latitude">
          <el-input-number v-model="form.latitude" :precision="6" :step="0.001" :min="-90" :max="90" style="width: 100%" />
        </el-form-item>
        <el-form-item label="车道数" prop="lane_count">
          <el-input-number v-model="form.lane_count" :min="1" :max="20" style="width: 100%" />
        </el-form-item>
        <el-form-item label="辖区">
          <el-input v-model="form.district" placeholder="如：城东辖区" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { fetchIntersections, createIntersection, updateIntersection, deleteIntersection } from '@/api/traffic'
import type { Intersection } from '@/api/traffic'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const rows = ref<Intersection[]>([])
const loading = ref(false)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref(0)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', longitude: 116.407, latitude: 39.904, lane_count: 4, district: '' })

const rules: FormRules = {
  name: [{ required: true, message: '请输入路口名称', trigger: 'blur' }],
  longitude: [{ required: true, message: '请输入经度', trigger: 'blur' }],
  latitude: [{ required: true, message: '请输入纬度', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const { data } = await fetchIntersections({ keyword: keyword.value })
    rows.value = data
  } finally {
    loading.value = false
  }
}

function openEdit(row?: Intersection) {
  editingId.value = row?.id ?? 0
  Object.assign(form, row ? { ...row } : { name: '', longitude: 116.407, latitude: 39.904, lane_count: 4, district: '' })
  dialogVisible.value = true
}

function goCalc(row: Intersection) {
  router.push({ path: '/traffic/signal-plans', query: { intersection_id: row.id } })
}

async function save() {
  await formRef.value?.validate()
  if (editingId.value) {
    await updateIntersection(editingId.value, { ...form })
  } else {
    await createIntersection({ ...form })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await load()
}

async function remove(row: Intersection) {
  await ElMessageBox.confirm(`确认删除路口「${row.name}」？`, '提示', { type: 'warning' })
  await deleteIntersection(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>
