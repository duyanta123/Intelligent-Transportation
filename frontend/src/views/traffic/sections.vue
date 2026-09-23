<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="路段名称" clearable style="width: 200px" @keyup.enter="load" />
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <span class="spacer" />
        <el-button v-if="auth.role === 'admin'" type="primary" :icon="Plus" @click="openEdit()">新增路段</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="路段名称" min-width="150" />
        <el-table-column label="起止路口" min-width="170">
          <template #default="{ row }">{{ row.start_name }} ↔ {{ row.end_name }}</template>
        </el-table-column>
        <el-table-column prop="lane_count" label="车道数" width="90" />
        <el-table-column prop="length_km" label="长度(km)" width="100" />
        <el-table-column prop="direction" label="走向" width="90" />
        <el-table-column prop="capacity" label="通行能力(pcu/h)" width="140" />
        <el-table-column v-if="auth.role === 'admin'" label="操作" width="140">
          <template #default="{ row }">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑路段' : '新增路段'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="路段名称" required>
          <el-input v-model="form.name" placeholder="如：中山路东段" />
        </el-form-item>
        <el-form-item label="起点路口" required>
          <el-select v-model="form.start_intersection_id" style="width: 100%">
            <el-option v-for="i in intersections" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="终点路口" required>
          <el-select v-model="form.end_intersection_id" style="width: 100%">
            <el-option v-for="i in intersections" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="车道数">
          <el-input-number v-model="form.lane_count" :min="1" :max="12" style="width: 100%" />
        </el-form-item>
        <el-form-item label="长度(km)">
          <el-input-number v-model="form.length_km" :min="0.1" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="走向">
          <el-radio-group v-model="form.direction">
            <el-radio value="东西">东西</el-radio>
            <el-radio value="南北">南北</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchSections, createSection, updateSection, deleteSection, fetchIntersections } from '@/api/traffic'
import type { RoadSection, Intersection } from '@/api/traffic'
import { sequenceGuard } from '@/utils/async'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const rows = ref<RoadSection[]>([])
const intersections = ref<Intersection[]>([])
const loading = ref(false)
const saving = ref(false)
const listSeq = sequenceGuard()
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref(0)
const form = reactive({ name: '', start_intersection_id: 0, end_intersection_id: 0, lane_count: 4, length_km: 1.0, direction: '东西' })

async function load() {
  const seq = listSeq.begin()
  loading.value = true
  try {
    const { data } = await fetchSections({ keyword: keyword.value })
    if (listSeq.isCurrent(seq)) rows.value = data
  } finally {
    if (listSeq.isCurrent(seq)) loading.value = false
  }
}

function openEdit(row?: RoadSection) {
  editingId.value = row?.id ?? 0
  Object.assign(
    form,
    row
      ? { ...row }
      : { name: '', start_intersection_id: intersections.value[0]?.id ?? 0, end_intersection_id: intersections.value[0]?.id ?? 0, lane_count: 4, length_km: 1.0, direction: '东西' },
  )
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim() || !form.start_intersection_id || !form.end_intersection_id) {
    ElMessage.warning('请完整填写路段信息')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateSection(editingId.value, { ...form })
    } else {
      await createSection({ ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row: RoadSection) {
  try {
    await ElMessageBox.confirm(`确认删除路段「${row.name}」？`, '提示', { type: 'warning' })
  } catch {
    return // 用户取消
  }
  await deleteSection(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(async () => {
  await load()
  const { data } = await fetchIntersections()
  intersections.value = data
})
</script>
