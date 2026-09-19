<template>
  <div class="page">
    <el-row :gutter="14">
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
                <el-input-number v-model="row.lanes" :min="1" :max="12" controls-position="right" style="width: 100%" />
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
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Delete, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchIntersections, fetchSignalPlans, createSignalPlan, deleteSignalPlan, calcWebster } from '@/api/traffic'
import type { Intersection, SignalPlan } from '@/api/traffic'
import { websterCalc } from '@/utils/algorithms'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const intersections = ref<Intersection[]>([])
const plans = ref<SignalPlan[]>([])
const loading = ref(false)
const filterId = ref<number | ''>('')
const calcLoading = ref(false)

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
  await createSignalPlan({
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

onMounted(async () => {
  const { data } = await fetchIntersections()
  intersections.value = data
  const preset = route.query.intersection_id
  if (preset) {
    filterId.value = Number(preset)
  }
  await loadPlans()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.phase-tag {
  margin: 2px 4px 2px 0;
}
</style>
