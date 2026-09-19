<template>
  <div class="page">
    <el-row :gutter="14">
      <!-- 拥堵一览 -->
      <el-col :span="9">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时拥堵（按路段最新记录）</span>
              <el-button text type="primary" @click="loadCongestion">刷新</el-button>
            </div>
          </template>
          <el-table v-loading="congestionLoading" :data="congestions" size="small" max-height="420">
            <el-table-column prop="name" label="路段" min-width="120" show-overflow-tooltip />
            <el-table-column prop="flow" label="流率" width="80" />
            <el-table-column prop="speed" label="车速" width="80">
              <template #default="{ row }">{{ row.speed }} km/h</template>
            </el-table-column>
            <el-table-column label="等级" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="levelType(row.level)" effect="dark">{{ row.level_name }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 历史查询 + 图表 -->
      <el-col :span="15">
        <el-card shadow="never">
          <template #header>历史流量查询</template>
          <div class="page-toolbar">
            <el-select v-model="query.section_id" placeholder="全部路段" clearable filterable style="width: 200px">
              <el-option v-for="s in sections" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
            <el-radio-group v-model="query.granularity">
              <el-radio-button value="hour">按小时</el-radio-button>
              <el-radio-button value="day">按天</el-radio-button>
            </el-radio-group>
            <el-button type="primary" @click="loadHistory">查询</el-button>
            <el-button plain :icon="Download" @click="doExport">导出日报</el-button>
            <span v-if="canReport" class="spacer" />
            <el-button v-if="canReport" type="success" plain @click="reportVisible = true">模拟上报</el-button>
          </div>
          <v-chart :option="historyOption" style="height: 330px" autoresize />
          <el-pagination
            v-model:current-page="page"
            :page-size="size"
            :total="total"
            layout="total, prev, pager, next"
            class="pager"
            @current-change="loadHistory"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 模拟上报弹窗 -->
    <el-dialog v-model="reportVisible" title="流量数据上报（模拟检测器）" width="420px">
      <el-form label-width="110px">
        <el-form-item label="路段" required>
          <el-select v-model="reportForm.road_section_id" style="width: 100%">
            <el-option v-for="s in sections" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分钟流量(辆)" required>
          <el-input-number v-model="reportForm.flow" :min="0" :max="500" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportVisible = false">取消</el-button>
        <el-button type="primary" @click="doReport">上报</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { downloadFile } from '@/api/download'
import { fetchSections, fetchFlowHistory, fetchCongestion, reportFlow } from '@/api/traffic'
import type { RoadSection } from '@/api/traffic'
import { useAuthStore } from '@/stores/auth'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const auth = useAuthStore()
const canReport = computed(() => auth.role === 'admin' || auth.role === 'officer')

const sections = ref<RoadSection[]>([])
const congestions = ref<Record<string, unknown>[]>([])
const congestionLoading = ref(false)
const loading = ref(false)
const page = ref(1)
const size = ref(48)
const total = ref(0)
const query = reactive({ section_id: undefined as number | undefined, granularity: 'hour' })
const historyRows = ref<{ time: string; avg_flow: number; max_flow: number; avg_speed: number }[]>([])
const reportVisible = ref(false)
const reportForm = reactive({ road_section_id: 0, flow: 20 })

const levelType = (level: number) => (['success', '', 'warning', 'danger'] as const)[level] ?? 'info'

const historyOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['平均流率', '峰值流率'] },
  grid: { left: 55, right: 20, top: 40, bottom: 60 },
  xAxis: { type: 'category', data: historyRows.value.map((r) => (query.granularity === 'hour' ? r.time.slice(5, 16) : r.time.slice(0, 10))) },
  yAxis: { type: 'value', name: 'pcu/h' },
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8 }],
  series: [
    { name: '平均流率', type: 'line', smooth: true, data: historyRows.value.map((r) => r.avg_flow), itemStyle: { color: '#409eff' } },
    { name: '峰值流率', type: 'line', smooth: true, data: historyRows.value.map((r) => r.max_flow), itemStyle: { color: '#e6a23c' } },
  ],
}))

function doExport() {
  downloadFile('/export/traffic-report.xlsx', { days: 7 }, `流量日报_${new Date().toISOString().slice(0, 10).replaceAll('-', '')}.xlsx`)
}

async function loadCongestion() {
  congestionLoading.value = true
  try {
    const { data } = await fetchCongestion()
    congestions.value = data.sections
  } finally {
    congestionLoading.value = false
  }
}

async function loadHistory() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { granularity: query.granularity, page: page.value, size: size.value }
    if (query.section_id) params.road_section_id = query.section_id
    const { data } = await fetchFlowHistory(params)
    historyRows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function doReport() {
  if (!reportForm.road_section_id) {
    ElMessage.warning('请选择路段')
    return
  }
  const { data } = await reportFlow({ road_section_id: reportForm.road_section_id, flow: reportForm.flow })
  ElMessage.success(`上报成功：折算 ${data.flow} pcu/h，${['自由流', '缓行', '拥堵', '严重拥堵'][data.congestion_level]}`)
  reportVisible.value = false
  await Promise.all([loadHistory(), loadCongestion()])
}

onMounted(async () => {
  const { data } = await fetchSections()
  sections.value = data
  await Promise.all([loadCongestion(), loadHistory()])
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pager {
  margin-top: 10px;
  justify-content: flex-end;
}
</style>
