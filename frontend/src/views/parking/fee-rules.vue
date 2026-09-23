<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <span class="hint">分时段计费：免费时长 → 首小时 → 每小时（不足按 1 小时）→ 单日封顶（每 24 小时一段）</span>
        <span class="spacer" />
        <el-button type="primary" :icon="Plus" @click="openEdit()">新增规则</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column prop="free_minutes" label="免费时长(分)" width="120" />
        <el-table-column prop="first_hour_fee" label="首小时(元)" width="110" />
        <el-table-column prop="hourly_fee" label="每小时(元)" width="110" />
        <el-table-column prop="daily_cap" label="单日封顶(元)" width="120" />
        <el-table-column label="示例：停 3 小时" width="120">
          <template #default="{ row }">{{ example(row) }} 元</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="免费时长(分)" prop="free_minutes">
          <el-input-number v-model="form.free_minutes" :min="0" :max="240" style="width: 100%" />
        </el-form-item>
        <el-form-item label="首小时(元)" prop="first_hour_fee">
          <el-input-number v-model="form.first_hour_fee" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="每小时(元)" prop="hourly_fee">
          <el-input-number v-model="form.hourly_fee" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单日封顶(元)" prop="daily_cap">
          <el-input-number v-model="form.daily_cap" :min="0" :precision="2" style="width: 100%" />
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
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { fetchFeeRules, createFeeRule, updateFeeRule, deleteFeeRule } from '@/api/parking'
import type { FeeRule } from '@/api/parking'
import { estimateParkingFee } from '@/utils/algorithms'

const rows = ref<FeeRule[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(0)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', free_minutes: 15, first_hour_fee: 5, hourly_fee: 3, daily_cap: 40 })

const rules: FormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  free_minutes: [{ required: true, message: '必填', trigger: 'blur' }],
  first_hour_fee: [{ required: true, message: '必填', trigger: 'blur' }],
  hourly_fee: [{ required: true, message: '必填', trigger: 'blur' }],
  daily_cap: [{ required: true, message: '必填', trigger: 'blur' }],
}

function example(row: FeeRule) {
  return estimateParkingFee(180, row.free_minutes, row.first_hour_fee, row.hourly_fee, row.daily_cap)
}

async function load() {
  loading.value = true
  try {
    const { data } = await fetchFeeRules()
    rows.value = data
  } finally {
    loading.value = false
  }
}

function openEdit(row?: FeeRule) {
  editingId.value = row?.id ?? 0
  Object.assign(form, row ?? { name: '', free_minutes: 15, first_hour_fee: 5, hourly_fee: 3, daily_cap: 40 })
  dialogVisible.value = true
}

async function save() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editingId.value) {
      await updateFeeRule(editingId.value, { ...form })
    } else {
      await createFeeRule({ ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row: FeeRule) {
  try {
    await ElMessageBox.confirm(`确认删除规则「${row.name}」？`, '提示', { type: 'warning' })
  } catch {
    return // 用户取消
  }
  await deleteFeeRule(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint {
  color: #909399;
  font-size: 13px;
}
</style>
