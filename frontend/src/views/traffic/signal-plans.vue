<template>
  <div class="page">
    <!-- 信号灯实时状态（10 秒轮询） -->
    <el-card shadow="never" class="status-card">
      <template #header>
        <div class="card-header">
          <span>信号灯实时状态（每 10 秒刷新）</span>
          <el-tag size="small" type="info">轮询中</el-tag>
        </div>
      </template>
      <el-row :gutter="12">
        <el-col v-for="s in signalStatus" :key="s.intersection_id" :xs="12" :sm="8" :md="6" :lg="6" style="margin-bottom: 10px">
          <div class="status-item" :class="{ dim: s.remaining_seconds <= 5 }">
            <div class="status-name">{{ s.intersection_name }}</div>
            <div class="status-phase">
              <span class="dot" :class="s.remaining_seconds <= 5 ? 'red' : 'green'" />
              {{ s.current_phase }}
            </div>
            <div class="status-meta">
              <span>剩余 {{ s.remaining_seconds }}s / 周期 {{ s.cycle_seconds }}s</span>
              <el-tag size="small" :type="s.mode === 'adaptive' ? 'warning' : 'primary'" effect="plain">
                {{ s.mode === 'adaptive' ? '感应' : '定周期' }}
              </el-tag>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="14" style="margin-top: 14px">
      <!-- Webster 配时计算器 -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>Webster 配时计算器（附录 D.2 参数：s=1800pcu/h/车道，每相位损失 6s）</template>
          <el-table :data="calcPhases" size="small">
            <el-table-column label="相位名" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.name" placeholder="如：南北直行" />
              </template>
            </el-table-column>
            <el-table-column label="车流量 pcu/h" width="150">
              <template #default="{ row }">
                <el-input-number v-model="row.flow" :min="1" :max="4000" controls-position="right" style="width: 100%" />
              </template>
            </el-table-column>
            <el-table-column label="车道数" width="130">
              <template #default="{ row }">
                <el-input-number v-model="row.lanes" :min="1" :max="12" step-strictly controls-position="right" style="width: 100%" />
              </template>
            </el-table-column>
            <el-table-column width="60">
              <template #default="{ $index }">
                <el-button text type="danger" :icon="Delete" @click="calcPhases.splice($index, 1)" />
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 10px; display: flex; gap: 10px">
            <el-button :icon="Plus" @click="addPhase">加相位</el-button>
            <el-button type="primary" :loading="calcLoading" @click="calc">计算最优周期</el-button>
          </div>

          <el-result v-if="calcResult" :icon="calcResult.oversaturated ? 'warning' : 'success'" :title="`最优周期 C0 = ${calcResult.cycle_seconds}s`" :sub-title="resultSummary">
            <el-table :data="calcResult.phases" size="small" style="margin-bottom: 12px">
              <el-table-column prop="name" label="相位" />
              <el-table-column prop="y" label="流量比 y" />
              <el-table-column prop="green" label="绿灯时长(s)">
                <template #default="{ row }">
                  <el-text type="success" size="large">{{ row.green }}</el-text>
                </template>
              </el-table-column>
            </el-table>
            <el-button type="success" @click="applyCalc">保存为配时方案</el-button>
          </el-result>
        </el-card>
      </el-col>

      <!-- 方案列表 -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>配时方案列表</span>
              <el-select v-model="filterId" placeholder="全部路口" clearable style="width: 180px" @change="loadPlans">
                <el-option v-for="i in intersections" :key="i.id" :label="i.name" :value="i.id" />
              </el-select>
            </div>
          </template>
          <el-table v-loading="loading" :data="plans" stripe size="small">
            <el-table-column prop="id" label="ID" width="55" />
            <el-table-column prop="intersection_name" label="路口" width="100" />
            <el-table-column prop="name" label="方案" min-width="140" show-overflow-tooltip />
            <el-table-column label="模式" width="105">
              <template #default="{ row }">
                <el-tag size="small" :type="row.mode === 'adaptive' ? 'warning' : 'primary'">{{ row.mode === 'adaptive' ? '感应自适应' : '定周期' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cycle_seconds" label="周期(s)" width="80" />
            <el-table-column label="绿信比" width="80">
              <template #default="{ row }">{{ (row.green_ratio * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="相位绿灯" min-width="200">
              <template #default="{ row }">
                <el-tag v-for="p in row.phases" :key="p.name" size="small" type="success" effect="plain" class="phase-tag">{{ p.name }} {{ p.green }}s</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="70">
              <template #default="{ row }">
                <el-icon v-if="row.is_active" color="#67c23a"><CircleCheckFilled /></el-icon>
              </template>
            </el-table-column>
            <el-table-column v-if="auth.role === 'admin'" label="操作" width="130">
              <template #default="{ row }">
                <el-button text type="primary" @click="activate(row)">启用</el-button>
                <el-button text type="danger" @click="remove(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 方案对比 -->
        <el-card shadow="never" style="margin-top: 14px">
          <template #header>
            <div class="card-header">
              <span>方案对比（任选两个方案对比相位绿灯分配）</span>
              <div style="display: flex; gap: 10px">
                <el-select v-model="compareA" placeholder="方案 A" clearable style="width: 220px">
                  <el-option v-for="p in plans" :key="p.id" :label="`${p.intersection_name} · ${p.name}`" :value="p.id" />
                </el-select>
                <el-select v-model="compareB" placeholder="方案 B" clearable style="width: 220px">
                  <el-option v-for="p in plans" :key="p.id" :label="`${p.intersection_name} · ${p.name}`" :value="p.id" />
                </el-select>
              </div>
            </div>
          </template>
          <v-chart v-if="compareA && compareB" :option="compareOption" style="height: 300px" autoresize />
          <el-empty v-else description="请选择两个配时方案进行对比" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Delete, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchIntersections, fetchSignalPlans, createSignalPlan, updateSignalPlan, deleteSignalPlan, calcWebster, fetchSignalStatus } from '@/api/traffic'
import type { Intersection, SignalPlan } from '@/api/traffic'
import { websterCalc } from '@/utils/algorithms'
import { useAuthStore } from '@/stores/auth'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const auth = useAuthStore()
const route = useRoute()
const intersections = ref<Intersection[]>([])
const plans = ref<SignalPlan[]>([])
const loading = ref(false)
const filterId = ref<number | ''>('')
const calcLoading = ref(false)

// ---- 方案对比 ----
const compareA = ref<number | ''>('')
const compareB = ref<number | ''>('')
const compareOption = computed(() => {
  const pa = plans.value.find((p) => p.id === compareA.value)
  const pb = plans.value.find((p) => p.id === compareB.value)
  if (!pa || !pb) return {}
  const phaseNames = [...new Set([...(pa.phases ?? []), ...(pb.phases ?? [])].map((p) => p.name))]
  const greenOf = (plan: SignalPlan, name: string) => plan.phases?.find((p) => p.name === name)?.green ?? 0
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: [pa.name, pb.name] },
    grid: { left: 55, right: 20, top: 50, bottom: 30 },
    xAxis: { type: 'category', data: phaseNames },
    yAxis: { type: 'value', name: '绿灯(s)' },
    series: [
      {
        name: `${pa.name}（周期 ${pa.cycle_seconds}s）`,
        type: 'bar',
        data: phaseNames.map((n) => greenOf(pa, n)),
        itemStyle: { color: '#409eff', borderRadius: 4 },
        barGap: '10%',
      },
      {
        name: `${pb.name}（周期 ${pb.cycle_seconds}s）`,
        type: 'bar',
        data: phaseNames.map((n) => greenOf(pb, n)),
        itemStyle: { color: '#e6a23c', borderRadius: 4 },
      },
    ],
  }
})

interface CalcPhase {
  name: string
  flow: number
  lanes: number
}
const calcPhases = ref<CalcPhase[]>([
  { name: '南北直行', flow: 1200, lanes: 2 },
  { name: '南北左转', flow: 400, lanes: 1 },
  { name: '东西直行', flow: 1000, lanes: 2 },
  { name: '东西左转', flow: 350, lanes: 1 },
])

const calcResult = ref<ReturnType<typeof websterCalc> | null>(null)

const resultSummary = computed(() =>
  calcResult.value
    ? `总损失 L=${calcResult.value.total_lost}s，Y=${calcResult.value.y_sum}${calcResult.value.oversaturated ? '，交叉口过饱和（Y≥0.95）按上限 180s 输出' : ''}`
    : '',
)

function addPhase() {
  calcPhases.value.push({ name: `相位${calcPhases.value.length + 1}`, flow: 500, lanes: 1 })
}

async function calc() {
  calcLoading.value = true
  try {
    // 先用前端纯函数预览，再调用后端同源实现做权威计算
    calcResult.value = websterCalc(calcPhases.value.map((p) => ({ ...p })))
    const { data } = await calcWebster(calcPhases.value)
    calcResult.value = data
  } catch (err) {
    // 不可行输入（如相位过多）：清除预览并提示（http 拦截器已弹出后端错误信息）
    calcResult.value = null
    if (err instanceof Error && err.message && !err.message.includes('Request failed')) {
      ElMessage.warning(err.message)
    }
  } finally {
    calcLoading.value = false
  }
}

async function applyCalc() {
  if (!calcResult.value) return
  const { value } = await ElMessageBox.prompt('请输入路口名称（保存为新方案）', '保存方案', { inputValue: '路口-方案', inputPattern: /\S+/ })
  const target = intersections.value.find((i) => i.name === value)
  if (!target) {
    ElMessage.warning('未找到该路口，请先在路口管理中创建')
    return
  }
  await createSignalPlan({
    intersection_id: target.id,
    name: `${target.name}-Webster配时方案`,
    mode: 'fixed',
    cycle_seconds: calcResult.value.cycle_seconds,
    phase_count: calcResult.value.phases.length,
    phases: calcResult.value.phases.map((p) => ({ name: p.name, green: p.green, yellow: 3, allRed: 1 })),
    is_active: false,
  })
  ElMessage.success('方案已保存')
  await loadPlans()
}

async function loadPlans() {
  loading.value = true
  try {
    const { data } = await fetchSignalPlans(filterId.value ? { intersection_id: filterId.value } : undefined)
    plans.value = data
  } finally {
    loading.value = false
  }
}

async function activate(row: SignalPlan) {
  // 用 PUT 更新启用状态（此前用 POST 重复创建同名方案，越点越多的脏数据就是这么来的）
  await updateSignalPlan(row.id, {
    intersection_id: row.intersection_id,
    name: row.name,
    mode: row.mode,
    cycle_seconds: row.cycle_seconds,
    phase_count: row.phase_count,
    phases: row.phases,
    is_active: true,
  })
  ElMessage.success(`已启用「${row.name}」`)
  await loadPlans()
}

async function remove(row: SignalPlan) {
  await ElMessageBox.confirm(`确认删除方案「${row.name}」？`, '提示', { type: 'warning' })
  await deleteSignalPlan(row.id)
  ElMessage.success('已删除')
  await loadPlans()
}

// ---- 信号灯实时状态轮询 ----
const signalStatus = ref<Record<string, unknown>[]>([])
let statusTimer: number | null = null

async function loadStatus() {
  try {
    const { data } = await fetchSignalStatus()
    signalStatus.value = data
  } catch {
    // 后端瞬断时静默降级（不 try/catch 的话每 10 秒弹一次错误 toast，永不停止）
  }
}

onMounted(async () => {
  try {
    const { data } = await fetchIntersections()
    intersections.value = data
  } catch {
    // 路口加载失败不阻断方案列表与轮询
  }
  const preset = route.query.intersection_id
  if (preset) {
    filterId.value = Number(preset)
  }
  await Promise.all([loadPlans(), loadStatus()])
  statusTimer = window.setInterval(loadStatus, 10000)
})

onBeforeUnmount(() => {
  if (statusTimer) window.clearInterval(statusTimer)
})
</script>

<style scoped>
.status-card :deep(.el-card__body) {
  padding-bottom: 4px;
}
.status-item {
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  padding: 10px 12px;
  transition: opacity 0.2s;
}
.status-item.dim {
  opacity: 0.65;
}
.status-name {
  font-weight: 600;
  color: #304156;
}
.status-phase {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 6px 0;
  color: #1f6fb2;
  font-size: 14px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot.green {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.7);
}
.dot.red {
  background: #f56c6c;
  box-shadow: 0 0 6px rgba(245, 108, 108, 0.7);
}
.status-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #8492a6;
  font-size: 12px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.phase-tag {
  margin: 2px 4px 2px 0;
}
</style>
