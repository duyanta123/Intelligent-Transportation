<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-input v-model="query.plate_no" placeholder="车牌号" clearable style="width: 160px" />
        <el-select v-model="query.violation_type" placeholder="违章类型" clearable style="width: 170px">
          <el-option v-for="t in typeCodes" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 130px">
          <el-option v-for="(name, key) in statusNames" :key="key" :label="name" :value="key" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <span class="spacer" />
        <el-button v-if="canManage" type="primary" :icon="Plus" @click="openCreate">录入违章</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="plate_no" label="车牌号" width="120">
          <template #default="{ row }">
            <el-tag effect="dark" type="warning">{{ row.plate_no }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="violation_type" label="类型" width="150" />
        <el-table-column prop="violation_time" label="时间" width="170" />
        <el-table-column prop="fine_amount" label="罚款(元)" width="95" />
        <el-table-column prop="deduct_points" label="记分" width="70" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="audit_remark" label="审核备注" min-width="140" show-overflow-tooltip />
        <el-table-column v-if="canManage" label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button text type="success" @click="audit(row, 'confirmed')">通过</el-button>
              <el-button text type="danger" @click="audit(row, 'rejected')">驳回</el-button>
            </template>
            <el-button v-if="row.status === 'confirmed'" text type="primary" @click="markProcessed(row)">标记已处理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next, sizes" class="pager" @current-change="load" @size-change="load" />
    </el-card>

    <!-- 录入违章 -->
    <el-dialog v-model="createVisible" title="录入违章" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="车牌号" prop="plate_no">
          <el-input v-model="form.plate_no" placeholder="如：京A12345" />
        </el-form-item>
        <el-form-item label="违章类型" prop="violation_type">
          <el-select v-model="form.violation_type" style="width: 100%" @change="applyPreset">
            <el-option v-for="t in typeCodes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="违章地点">
          <el-select v-model="form.intersection_id" placeholder="选择路口" clearable style="width: 100%">
            <el-option v-for="i in intersections" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="违章时间" required>
          <el-date-picker v-model="form.violation_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="罚款(元)">
          <el-input-number v-model="form.fine_amount" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="记分">
          <el-input-number v-model="form.deduct_points" :min="0" :max="12" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="save">提交并送审</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { fetchViolations, createViolation, auditViolation, processViolation, fetchViolationTypes } from '@/api/vehicle'
import { fetchIntersections } from '@/api/traffic'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canManage = computed(() => auth.role === 'admin' || auth.role === 'officer')
const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const typeCodes = ref<string[]>([])
const intersections = ref<Record<string, unknown>[]>([])
const statusNames: Record<string, string> = { pending: '待审核', confirmed: '已确认', rejected: '已驳回', processed: '已处理' }
const query = reactive({ plate_no: '', violation_type: '', status: '' })

const createVisible = ref(false)
const formRef = ref<FormInstance>()
const presets: Record<string, { fine: number; points: number }> = {}
const form = reactive({ plate_no: '', violation_type: '', intersection_id: undefined as number | undefined, violation_time: '', fine_amount: 0, deduct_points: 0, remark: '' })

const rules: FormRules = {
  plate_no: [
    { required: true, message: '请输入车牌号', trigger: 'blur' },
    { pattern: /^[京津沪渝冀晋辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云陕甘青蒙藏宁新][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,6}$/, message: '车牌号格式不正确', trigger: 'blur' },
  ],
  violation_type: [{ required: true, message: '请选择违章类型', trigger: 'change' }],
  violation_time: [{ required: true, message: '请选择违章时间', trigger: 'change' }],
}

const statusType = (status: string) => ({ pending: 'warning', confirmed: 'primary', rejected: 'danger', processed: 'success' }[status] ?? 'info') as never

function applyPreset(type: string) {
  const preset = presets[type]
  if (preset) {
    form.fine_amount = preset.fine
    form.deduct_points = preset.points
  }
}

async function load() {
  loading.value = true
  try {
    const { data } = await fetchViolations({ page: page.value, size: size.value, ...query })
    rows.value = data.list as never
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, { plate_no: '', violation_type: '', intersection_id: undefined, violation_time: new Date().toISOString().slice(0, 19), fine_amount: 0, deduct_points: 0, remark: '' })
  createVisible.value = true
}

async function save() {
  await formRef.value?.validate()
  await createViolation({ ...form })
  ElMessage.success('录入成功，等待审核')
  createVisible.value = false
  await load()
}

async function audit(row: Record<string, unknown>, result: string) {
  const isApprove = result === 'confirmed'
  const { value } = await ElMessageBox.prompt(isApprove ? '审核备注（可空）' : '请填写驳回原因', `${isApprove ? '通过' : '驳回'}违章 #${row.id}`, { inputValue: isApprove ? '证据清晰' : '证据不足' })
  await auditViolation(row.id as number, { result, remark: value ?? '' })
  ElMessage.success('审核完成')
  await load()
}

async function markProcessed(row: Record<string, unknown>) {
  await ElMessageBox.confirm(`确认违章 #${row.id}（${row.plate_no}）已处理完毕？`, '提示', { type: 'info' })
  await processViolation(row.id as number)
  ElMessage.success('已标记为已处理')
  await load()
}

onMounted(async () => {
  await load()
  const { data: types } = await fetchViolationTypes()
  for (const t of types) {
    if (typeof t.code === 'string') {
      typeCodes.value.push(t.code)
      presets[t.code] = { fine: Number(t.fine ?? 0), points: Number(t.points ?? 0) }
    }
  }
  const { data: inters } = await fetchIntersections()
  intersections.value = inters as never
})
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
