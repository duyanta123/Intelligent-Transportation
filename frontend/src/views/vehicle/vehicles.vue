<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="车牌号/车主/手机号" clearable style="width: 220px" @keyup.enter="load" />
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <span class="spacer" />
        <el-button v-if="canManage" type="primary" :icon="Plus" @click="openEdit()">登记车辆</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="plate_no" label="车牌号" width="130">
          <template #default="{ row }">
            <el-tag effect="dark" type="primary">{{ row.plate_no }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vehicle_type" label="车辆类型" width="140" />
        <el-table-column prop="color" label="颜色" width="90" />
        <el-table-column prop="owner_name" label="车主" width="110" />
        <el-table-column prop="owner_phone" label="联系电话" width="130" />
        <el-table-column prop="created_at" label="登记时间" width="170" />
        <el-table-column v-if="canManage" label="操作" width="150">
          <template #default="{ row }">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="auth.role === 'admin'" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next, sizes" class="pager" @current-change="load" @size-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑车辆' : '登记车辆'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="车牌号" prop="plate_no">
          <el-input v-model="form.plate_no" placeholder="如：京A12345 或 京AD12345（新能源）" style="text-transform: uppercase" />
        </el-form-item>
        <el-form-item label="车辆类型">
          <el-select v-model="form.vehicle_type" style="width: 100%">
            <el-option v-for="t in types" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="颜色">
          <el-select v-model="form.color" style="width: 100%">
            <el-option v-for="c in colors" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="车主姓名">
          <el-input v-model="form.owner_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.owner_phone" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { fetchVehicles, createVehicle, updateVehicle, deleteVehicle } from '@/api/vehicle'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canManage = computed(() => auth.role === 'admin' || auth.role === 'officer')
const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(0)
const formRef = ref<FormInstance>()
const types = ['小型汽车', '小型新能源汽车', '大型汽车', '挂车']
const colors = ['白色', '黑色', '银色', '蓝色', '红色', '绿色']
const form = reactive({ plate_no: '', vehicle_type: '小型汽车', color: '白色', owner_name: '', owner_phone: '' })

// 车牌校验：省份简称 + 字母 + 4~6 位序号（支持新能源 8 位）
const platePattern = /^[京津沪渝冀晋辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云陕甘青蒙藏宁新][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,6}$/
const rules: FormRules = {
  plate_no: [
    { required: true, message: '请输入车牌号', trigger: 'blur' },
    { pattern: platePattern, message: '车牌号格式不正确（支持新能源 8 位牌）', trigger: 'blur' },
  ],
}

async function load() {
  loading.value = true
  try {
    const { data } = await fetchVehicles({ page: page.value, size: size.value, keyword: keyword.value })
    rows.value = data.list as never
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openEdit(row?: Record<string, unknown>) {
  editingId.value = (row?.id as number) ?? 0
  Object.assign(
    form,
    row
      ? { plate_no: row.plate_no, vehicle_type: row.vehicle_type, color: row.color, owner_name: row.owner_name, owner_phone: row.owner_phone }
      : { plate_no: '', vehicle_type: '小型汽车', color: '白色', owner_name: '', owner_phone: '' },
  )
  dialogVisible.value = true
}

async function save() {
  await formRef.value?.validate()
  if (editingId.value) {
    await updateVehicle(editingId.value, { ...form })
  } else {
    await createVehicle({ ...form })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await load()
}

async function remove(row: Record<string, unknown>) {
  await ElMessageBox.confirm(`确认删除车辆「${row.plate_no}」？`, '提示', { type: 'warning' })
  await deleteVehicle(row.id as number)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
