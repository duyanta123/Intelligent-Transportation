<template>
  <div class="page">
    <!-- 核心指标卡 -->
    <el-row :gutter="14">
      <el-col v-for="card in cards" :key="card.label" :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" :style="{ background: card.color }">
              <el-icon :size="26"><component :is="card.icon" /></el-icon>
            </div>
            <div>
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" class="mt14">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>近 7 天平均流量趋势（pcu/h）</template>
          <v-chart :option="trendOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>违章类型分布</template>
          <v-chart :option="typeOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" class="mt14">
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>停车场占用</template>
          <el-table :data="summary.parking ?? []" size="small">
            <el-table-column prop="name" label="停车场" />
            <el-table-column label="占用率">
              <template #default="{ row }">
                <el-progress :percentage="row.rate" :stroke-width="14" :color="row.rate > 85 ? '#f56c6c' : '#67c23a'" />
              </template>
            </el-table-column>
            <el-table-column label="占用/总数" width="110">
              <template #default="{ row }">{{ row.used }}/{{ row.total }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col v-if="auth.role === 'admin'" :span="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近操作日志</span>
              <el-button text type="primary" @click="$router.push('/system/logs')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="logs" size="small">
            <el-table-column prop="username" label="操作人" width="90" />
            <el-table-column prop="action" label="操作" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="actionTagType(row.action)">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="detail" label="详情" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchSummary, fetchAdminStats, fetchRecentLogs } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const auth = useAuthStore()
const stats = ref<Record<string, number>>({})
const summary = ref<{ flow_trend?: { date: string; flow: number }[]; violation_types?: { name: string; value: number }[]; parking?: { name: string; total: number; used: number; rate: number }[] }>({})
const logs = ref<Record<string, string>[]>([])

const cards = computed(() => [
  { label: '注册用户数', value: stats.value.user_count ?? '-', icon: 'User', color: '#409eff' },
  { label: '登记车辆数', value: stats.value.vehicle_count ?? '-', icon: 'Van', color: '#67c23a' },
  { label: '今日新增违章', value: stats.value.violation_today ?? '-', icon: 'Warning', color: '#e6a23c' },
  { label: '待处理事项', value: stats.value.feedback_pending ?? '-', icon: 'ChatDotRound', color: '#f56c6c' },
])

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: summary.value.flow_trend?.map((r) => r.date.slice(5)) ?? [] },
  yAxis: { type: 'value' },
  series: [{ type: 'line', smooth: true, data: summary.value.flow_trend?.map((r) => r.flow) ?? [], areaStyle: {}, itemStyle: { color: '#409eff' } }],
}))

const typeOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['38%', '65%'],
      data: summary.value.violation_types ?? [],
      label: { formatter: '{b}: {c}' },
    },
  ],
}))

function actionTagType(action: string) {
  if (action === '删除') return 'danger'
  if (action === '登录' || action === '登出') return 'info'
  if (action === '审核' || action === '受理') return 'warning'
  return 'success'
}

onMounted(async () => {
  const [statsResp, summaryResp] = await Promise.all([fetchAdminStats(), fetchSummary()])
  stats.value = statsResp.data
  summary.value = summaryResp.data as typeof summary.value
  if (auth.role === 'admin') {
    const logsResp = await fetchRecentLogs(8)
    logs.value = logsResp.data
  }
})
</script>

<style scoped>
.mt14 {
  margin-top: 14px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2d3d;
}
.stat-label {
  font-size: 13px;
  color: #8492a6;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
