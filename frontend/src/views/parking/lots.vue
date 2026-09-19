<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>停车场列表（普通用户可查看剩余车位）</template>
      <el-row :gutter="14">
        <el-col v-for="lot in rows" :key="lot.id" :span="12">
          <el-card shadow="hover" class="lot-card">
            <div class="lot-head">
              <div>
                <div class="lot-name">{{ lot.name }}</div>
                <div class="lot-addr">{{ lot.address }}</div>
              </div>
              <el-tag :type="occupancyType(lot)" effect="dark" size="large">{{ lot.free_slots }} 空闲</el-tag>
            </div>
            <el-progress :percentage="lot.occupancy" :stroke-width="16" :color="progressColor(lot)" style="margin-top: 12px" />
            <div class="lot-meta">
              <span>车位：{{ lot.used_slots }}/{{ lot.total_slots }}</span>
              <span v-if="lot.fee_rule_name">计费：{{ lot.fee_rule_name }}</span>
            </div>
            <div v-if="auth.role !== 'user'" class="lot-actions">
              <el-button v-if="auth.role === 'admin'" text type="primary" @click="openEdit(lot)">编辑</el-button>
              <el-button v-if="auth.role === 'admin'" text type="danger" @click="remove(lot)">删除</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <div v-if="auth.role === 'admin'" style="margin-top: 10px">
        <el-button type="primary" :icon="Plus" @click="openEdit()">新增停车场</el-button>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑停车场' : '新增停车场'" width="480px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-form-item label="车位总数" required>
          <el-input-number v-model="form.total_slots" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="当前占用">
          <el-input-number v-model="form.used_slots" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="计费规则">
          <el-select v-model="form.fee_rule_id" clearable style="width: 100%">
            <el-option v-for="r in rules" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
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
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchParkingLots, createParkingLot, updateParkingLot, deleteParkingLot, fetchFeeRules } from '@/api/parking'
import type { ParkingLot, FeeRule } from '@/api/parking'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const rows = ref<ParkingLot[]>([])
const rules = ref<FeeRule[]>([])
const dialogVisible = ref(false)
const editingId = ref(0)
const form = reactive({ name: '', address: '', total_slots: 100, used_slots: 0, fee_rule_id: undefined as number | undefined })

const progressColor = (lot: ParkingLot) => (lot.occupancy > 85 ? '#f56c6c' : lot.occupancy > 60 ? '#e6a23c' : '#67c23a')
const occupancyType = (lot: ParkingLot) => (lot.free_slots === 0 ? 'danger' : lot.occupancy > 60 ? 'warning' : 'success') as never

async function load() {
  const { data } = await fetchParkingLots()
  rows.value = data
}

function openEdit(lot?: ParkingLot) {
  editingId.value = lot?.id ?? 0
  Object.assign(
    form,
    lot
      ? { name: lot.name, address: lot.address, total_slots: lot.total_slots, used_slots: lot.used_slots, fee_rule_id: lot.fee_rule_id ?? undefined }
      : { name: '', address: '', total_slots: 100, used_slots: 0, fee_rule_id: rules.value[0]?.id },
  )
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  if (editingId.value) {
    await updateParkingLot(editingId.value, { ...form })
  } else {
    await createParkingLot({ ...form })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await load()
}

async function remove(lot: ParkingLot) {
  await ElMessageBox.confirm(`确认删除停车场「${lot.name}」？`, '提示', { type: 'warning' })
  await deleteParkingLot(lot.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(async () => {
  await load()
  const { data } = await fetchFeeRules()
  rules.value = data
})
</script>

<style scoped>
.lot-card {
  margin-bottom: 14px;
}
.lot-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.lot-name {
  font-size: 17px;
  font-weight: 600;
}
.lot-addr {
  color: #8492a6;
  font-size: 13px;
  margin-top: 4px;
}
.lot-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  color: #606266;
  font-size: 13px;
}
.lot-actions {
  margin-top: 6px;
  text-align: right;
}
</style>
