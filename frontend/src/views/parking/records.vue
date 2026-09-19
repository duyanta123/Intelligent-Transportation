<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-select v-model="query.parking_lot_id" placeholder="全部停车场" clearable style="width: 200px">
          <el-option v-for="lot in lots" :key="lot.id" :label="lot.name" :value="lot.id" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px">
          <el-option label="在场" value="inside" />
          <el-option label="已出场" value="finished" />
        </el-select>
        <el-input v-model="query.plate_no" placeholder="车牌号" clearable style="width: 160px" />
        <el-date-picker
          v-model="enterRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="入场开始"
          end-placeholder="入场结束"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 340px"
        />
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <span class="spacer" />
        <el-button type="success" :icon="Upload" @click="enterVisible = true">车辆入场</el-button>
        <el-button type="info" plain :icon="Download" @click="doExport">导出 Excel</el-button>
        <el-button type="warning" :icon="Download" @click="exitVisible = true">车辆出场</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="parking_lot_name" label="停车场" min-width="150" show-overflow-tooltip />
        <el-table-column prop="plate_no" label="车牌号" width="120">
          <template #default="{ row }">
            <el-tag effect="dark" type="primary">{{ row.plate_no }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enter_time" label="入场时间" width="170" />
        <el-table-column prop="exit_time" label="出场时间" width="170">
          <template #default="{ row }">{{ row.exit_time || '—' }}</template>
        </el-table-column>
        <el-table-column label="费用(元)" width="100">
          <template #default="{ row }">{{ row.fee ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'inside' ? 'warning' : 'success'">{{ row.status === 'inside' ? '在场' : '已出场' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入场拍照" width="100">
          <template #default="{ row }">
            <el-image v-if="row.image_url" :src="row.image_url" :preview-src-list="[row.image_url]" preview-teleported fit="cover" style="width: 56px; height: 40px; border-radius: 4px" />
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next, sizes" class="pager" @current-change="load" @size-change="load" />
    </el-card>

    <!-- 入场 -->
    <el-dialog v-model="enterVisible" title="车辆入场（可上传入场拍照）" width="440px">
      <el-form label-width="90px">
        <el-form-item label="停车场" required>
          <el-select v-model="enterForm.parking_lot_id" style="width: 100%">
            <el-option v-for="lot in lots" :key="lot.id" :label="`${lot.name}（剩 ${lot.free_slots}）`" :value="lot.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="车牌号" required>
          <el-input v-model="enterForm.plate_no" placeholder="如：京A12345" />
        </el-form-item>
        <el-form-item label="入场拍照">
          <input type="file" accept=".jpg,.jpeg,.png,.webp" @change="onFileChange" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="enterVisible = false">取消</el-button>
        <el-button type="primary" @click="doEnter">入场登记</el-button>
      </template>
    </el-dialog>

    <!-- 出场 -->
    <el-dialog v-model="exitVisible" title="车辆出场结算" width="420px">
      <el-form label-width="90px">
        <el-form-item label="停车场" required>
          <el-select v-model="exitForm.parking_lot_id" style="width: 100%">
            <el-option v-for="lot in lots" :key="lot.id" :label="lot.name" :value="lot.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="车牌号" required>
          <el-input v-model="exitForm.plate_no" placeholder="如：京A12345" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exitVisible = false">取消</el-button>
        <el-button type="primary" @click="doExit">出场结算</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Search, Upload, Download } from '@element-plus/icons-vue'
import { downloadFile } from '@/api/download'
import { ElMessage } from 'element-plus'
import { fetchParkingLots, parkingEnter, parkingExit, fetchParkingRecords } from '@/api/parking'
import type { ParkingLot } from '@/api/parking'

const lots = ref<ParkingLot[]>([])
const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const query = reactive({ parking_lot_id: undefined as number | undefined, status: '', plate_no: '' })
const enterRange = ref<[string, string] | null>(null)

const enterVisible = ref(false)
const exitVisible = ref(false)
const enterForm = reactive({ parking_lot_id: 0, plate_no: '', file: null as File | null })
const exitForm = reactive({ parking_lot_id: 0, plate_no: '' })

function onFileChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  enterForm.file = files && files.length > 0 ? files[0] : null
}

function doExport() {
  downloadFile('/export/parking-records.xlsx', { days: 30 }, `出入场记录_${new Date().toISOString().slice(0, 10).replaceAll('-', '')}.xlsx`)
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    if (query.parking_lot_id) params.parking_lot_id = query.parking_lot_id
    if (query.status) params.status = query.status
    if (query.plate_no) params.plate_no = query.plate_no
    if (enterRange.value) {
      params.enter_start = enterRange.value[0]
      params.enter_end = enterRange.value[1]
    }
    const { data } = await fetchParkingRecords(params)
    rows.value = data.list as never
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function doEnter() {
  if (!enterForm.parking_lot_id || !enterForm.plate_no.trim()) {
    ElMessage.warning('请选择停车场并输入车牌号')
    return
  }
  const fd = new FormData()
  fd.append('parking_lot_id', String(enterForm.parking_lot_id))
  fd.append('plate_no', enterForm.plate_no.trim().toUpperCase())
  if (enterForm.file) fd.append('file', enterForm.file)
  const { data } = await parkingEnter(fd)
  ElMessage.success(`入场成功：${data.plate_no} @ ${data.enter_time}`)
  enterVisible.value = false
  await load()
}

async function doExit() {
  if (!exitForm.parking_lot_id || !exitForm.plate_no.trim()) {
    ElMessage.warning('请选择停车场并输入车牌号')
    return
  }
  const { data } = await parkingExit({ parking_lot_id: exitForm.parking_lot_id, plate_no: exitForm.plate_no.trim().toUpperCase() })
  ElMessage.success(`出场成功，结算费用 ${data.fee} 元`)
  exitVisible.value = false
  await load()
}

onMounted(async () => {
  await load()
  const { data } = await fetchParkingLots()
  lots.value = data
})
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
