<template>
  <div class="screen-viewport">
    <div class="screen" :style="{ transform: `scale(${scale})` }">
      <!-- 顶部标题 -->
      <header class="header">
        <div class="header-side left">
          <span class="badge">SMART TRAFFIC</span>
        </div>
        <h1 class="title">智慧交通综合管理数据大屏</h1>
        <div class="header-side right">
          <span class="clock">{{ clock }}</span>
        </div>
      </header>

      <!-- 指标卡 -->
      <section class="kpi-row">
        <div v-for="card in kpis" :key="card.label" class="kpi-card">
          <div class="kpi-icon" :style="{ color: card.color, borderColor: card.color }">
            <span class="kpi-num">{{ card.value }}</span>
            <span class="kpi-unit">{{ card.unit }}</span>
          </div>
          <div class="kpi-label">{{ card.label }}</div>
        </div>
      </section>

      <!-- 图表区 -->
      <section class="charts-row">
        <div class="col">
          <panel title="全市车流量 24 小时趋势">
            <div ref="trendRef" class="chart" />
          </panel>
          <panel title="今日违章类型 TOP5">
            <div ref="violationRef" class="chart" />
          </panel>
        </div>
        <div class="col middle">
          <panel title="各路口实时拥堵态势" height="630px">
            <div ref="mapRef" class="chart map-chart" />
          </panel>
          <div class="legend-bar">
            <span v-for="(name, i) in LEVEL_NAMES" :key="name" class="legend-item">
              <i :style="{ background: LEVEL_COLORS[i] }" />{{ name }}
            </span>
          </div>
        </div>
        <div class="col">
          <panel title="信号灯状态分布">
            <div ref="signalRef" class="chart" />
          </panel>
          <panel title="停车场车位占用率">
            <div ref="parkingRef" class="chart" />
          </panel>
        </div>
      </section>

      <footer class="footer">
        数据每 10 秒自动刷新 · 最近更新：{{ data?.updated_at ?? '—' }}
      </footer>
    </div>

    <!-- 后端不可用降级提示 -->
    <div v-if="degraded" class="degrade-mask">
      <div class="degrade-card">
        <el-icon :size="54" color="#f56c6c"><WarningFilled /></el-icon>
        <h2>后端服务连接失败</h2>
        <p>数据大屏依赖后端 API（127.0.0.1:8000），请确认服务已启动后重试。</p>
        <el-button type="primary" size="large" @click="loadData">重新连接</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, type PropType } from 'vue'
import * as echarts from 'echarts'
import { WarningFilled } from '@element-plus/icons-vue'
import { fetchRealtime, type RealtimeData } from '@/api/dashboard'

const LEVEL_NAMES = ['自由流', '缓行', '拥堵', '严重拥堵']
const LEVEL_COLORS = ['#2ec7c9', '#f6e58d', '#ff9f43', '#ee5253']

/** 通用面板（标题 + 发光边框） */
const panel = defineComponent({
  name: 'ScreenPanel',
  props: { title: String, height: { type: String as PropType<string | undefined>, default: '305px' } },
  setup(props, { slots }) {
    return () =>
      h('div', { class: 'panel', style: { height: props.height } }, [
        h('div', { class: 'panel-title' }, props.title),
        h('div', { class: 'panel-body' }, slots.default?.()),
      ])
  },
})

const data = ref<RealtimeData | null>(null)
const degraded = ref(false)
const clock = ref('')
const scale = ref(1)

const trendRef = ref<HTMLElement>()
const mapRef = ref<HTMLElement>()
const signalRef = ref<HTMLElement>()
const parkingRef = ref<HTMLElement>()
const violationRef = ref<HTMLElement>()

let trendChart: echarts.ECharts | null = null
let mapChart: echarts.ECharts | null = null
let signalChart: echarts.ECharts | null = null
let parkingChart: echarts.ECharts | null = null
let violationChart: echarts.ECharts | null = null
let refreshTimer: number | null = null
let clockTimer: number | null = null

/** KPI 数字滚动动画：每次数据刷新从当前显示值缓动到目标值 */
const kpiDisplay = ref<number[]>([0, 0, 0, 0])
const kpiTargets = computed(() => {
  const k = data.value?.kpi
  return k ? [k.today_flow, k.avg_speed, k.violation_today, k.feedback_pending] : [0, 0, 0, 0]
})
const kpiFormatters: ((v: number) => string)[] = [
  (v) => Math.round(v).toLocaleString(),
  (v) => v.toFixed(1),
  (v) => String(Math.round(v)),
  (v) => String(Math.round(v)),
]
let tweenRaf: number | null = null
function tweenKpis() {
  if (tweenRaf) cancelAnimationFrame(tweenRaf)
  const startVals = [...kpiDisplay.value]
  const targets = kpiTargets.value
  const t0 = performance.now()
  const duration = 600
  const step = (t: number) => {
    const p = Math.min(1, (t - t0) / duration)
    const eased = 1 - Math.pow(1 - p, 3)
    kpiDisplay.value = startVals.map((s, i) => s + (targets[i] - s) * eased)
    if (p < 1) tweenRaf = requestAnimationFrame(step)
  }
  tweenRaf = requestAnimationFrame(step)
}

const kpis = computed(() => [
  { label: '今日车流量', value: kpiFormatters[0](kpiDisplay.value[0]), unit: 'pcu', color: '#38bdf8' },
  { label: '平均车速', value: kpiFormatters[1](kpiDisplay.value[1]), unit: 'km/h', color: '#4ade80' },
  { label: '今日违章数', value: kpiFormatters[2](kpiDisplay.value[2]), unit: '起', color: '#fbbf24' },
  { label: '投诉待处理', value: kpiFormatters[3](kpiDisplay.value[3]), unit: '件', color: '#f472b6' },
])

/** 模拟城市边界 geoJSON（不接真实地图，仅用于坐标定位） */
function buildCityGeoJson() {
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { name: '演示城市' },
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [116.355, 39.875], [116.405, 39.868], [116.455, 39.882], [116.465, 39.915],
              [116.435, 39.945], [116.39, 39.948], [116.358, 39.93], [116.348, 39.905], [116.355, 39.875],
            ],
          ],
        },
      },
    ],
  }
}

function initCharts() {
  if (trendRef.value) trendChart = echarts.init(trendRef.value)
  if (violationRef.value) violationChart = echarts.init(violationRef.value)
  if (signalRef.value) signalChart = echarts.init(signalRef.value)
  if (parkingRef.value) parkingChart = echarts.init(parkingRef.value)
  if (mapRef.value) {
    echarts.registerMap('smartcity', buildCityGeoJson() as never)
    mapChart = echarts.init(mapRef.value)
  }
}

function renderCharts() {
  if (!data.value) return
  // 1. 24h 流量趋势
  trendChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 22, bottom: 26 },
    xAxis: { type: 'category', data: data.value.flow_trend.map((r) => r.time), axisLabel: { color: '#9fb8d0' }, boundaryGap: false },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(120,160,200,0.15)' } }, axisLabel: { color: '#9fb8d0' } },
    series: [
      { type: 'line', smooth: true, data: data.value.flow_trend.map((r) => r.flow), symbol: 'none', lineStyle: { color: '#38bdf8', width: 2 }, areaStyle: { color: 'rgba(56,189,248,0.25)' } },
    ],
  })
  // 2. 违章 TOP5 柱状
  const top = [...data.value.violation_top].reverse()
  violationChart?.setOption({
    tooltip: {},
    grid: { left: 110, right: 24, top: 12, bottom: 22 },
    xAxis: { type: 'value', axisLabel: { color: '#9fb8d0' }, splitLine: { lineStyle: { color: 'rgba(120,160,200,0.15)' } } },
    yAxis: { type: 'category', data: top.map((r) => r.name), axisLabel: { color: '#cfe3f5' } },
    series: [{ type: 'bar', data: top.map((r) => r.value), barWidth: 14, itemStyle: { color: '#fbbf24', borderRadius: 7 } }],
  })
  // 3. 信号灯状态分布（饼图）
  signalChart?.setOption({
    tooltip: {},
    legend: { bottom: 0, textStyle: { color: '#9fb8d0' } },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '44%'],
        data: data.value.signal_dist,
        label: { color: '#cfe3f5', formatter: '{b}\n{c}' },
        itemStyle: { borderRadius: 6 },
        color: ['#4ade80', '#f6e58d', '#ff9f43', '#38bdf8', '#ee5253', '#a78bfa'],
      },
    ],
  })
  // 4. 停车场占用率（横向条形）
  parkingChart?.setOption({
    tooltip: { formatter: (p: { name: string; value: number }) => `${p.name}：${p.value}%` },
    grid: { left: 130, right: 40, top: 18, bottom: 24 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: '#9fb8d0' } },
    yAxis: { type: 'category', data: data.value.parking.map((p) => p.name), axisLabel: { color: '#cfe3f5' } },
    series: [
      {
        type: 'bar',
        data: data.value.parking.map((p) => p.rate),
        barWidth: 18,
        itemStyle: { borderRadius: 9 },
        color: ['#4ade80'],
        label: { show: true, position: 'right', formatter: '{c}%', color: '#cfe3f5' },
      },
    ],
  })
  // 5. 地图：路网连线（按拥堵等级着色 + 流光）+ 路口散点
  const roads = data.value.roads ?? []
  mapChart?.setOption({
    geo: {
      map: 'smartcity',
      roam: false,
      itemStyle: { areaColor: 'rgba(35,80,130,0.45)', borderColor: '#3d7ea6', borderWidth: 1.5 },
      emphasis: { disabled: true },
    },
    series: [
      {
        name: '路网',
        type: 'lines',
        coordinateSystem: 'geo',
        polyline: false,
        data: roads.map((r) => ({
          name: r.name,
          coords: r.coords,
          lineStyle: { color: LEVEL_COLORS[r.level] },
        })),
        lineStyle: { width: 3.5, opacity: 0.75, cap: 'round', curveness: 0 },
        effect: {
          show: true,
          period: 5,
          trailLength: 0.35,
          symbol: 'arrow',
          symbolSize: 6,
          color: '#ffffff',
        },
        tooltip: {
          formatter: (p: { name: string; data: { lineStyle: { color: string } } }) => {
            const road = roads.find((r) => r.name === p.name)
            return road ? `${p.name}<br/>拥堵等级：${LEVEL_NAMES[road.level]}<br/>流率：${road.flow} pcu/h · 车速：${road.speed} km/h` : p.name
          },
        },
      },
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        symbolSize: 26,
        data: data.value.map_points.map((p) => ({
          name: p.name,
          value: [p.lng, p.lat, p.level],
          level: p.level,
          itemStyle: { color: LEVEL_COLORS[p.level], shadowBlur: 14, shadowColor: LEVEL_COLORS[p.level] },
        })),
        label: {
          show: true,
          position: 'right',
          formatter: (p: { name: string }) => p.name,
          color: '#e8f4ff',
          fontSize: 12,
        },
      },
    ],
    tooltip: {
      formatter: (p: { name: string; data: { value: [number, number, number] } }) => {
        const level = p.data.value[2]
        return `${p.name}<br/>拥堵等级：${LEVEL_NAMES[level] ?? '未知'}`
      },
    },
  })
}

async function loadData() {
  try {
    const resp = await fetchRealtime()
    data.value = resp.data
    degraded.value = false
    renderCharts()
    tweenKpis()
  } catch {
    degraded.value = true
  }
}

function updateClock() {
  clock.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

function updateScale() {
  // scale 等比缩放适配（参考 GoView 方案）：设计稿 1920×1080
  scale.value = Math.min(window.innerWidth / 1920, window.innerHeight / 1080)
}

onMounted(() => {
  updateScale()
  updateClock()
  window.addEventListener('resize', updateScale)
  initCharts()
  loadData()
  refreshTimer = window.setInterval(loadData, 10000)
  clockTimer = window.setInterval(updateClock, 1000)
})

onBeforeUnmount(() => {
  if (tweenRaf) cancelAnimationFrame(tweenRaf)
  window.removeEventListener('resize', updateScale)
  if (refreshTimer) window.clearInterval(refreshTimer)
  if (clockTimer) window.clearInterval(clockTimer)
  for (const chart of [trendChart, mapChart, signalChart, parkingChart, violationChart]) chart?.dispose()
})
</script>

<style scoped>
.screen-viewport {
  width: 100%;
  height: 100%;
  background: #081c33;
  overflow: hidden;
  position: relative;
}
.screen {
  width: 1920px;
  height: 1080px;
  transform-origin: left top;
  display: flex;
  flex-direction: column;
  padding: 0 24px 12px;
  background:
    radial-gradient(1200px 500px at 50% -10%, rgba(35, 90, 150, 0.35), transparent),
    linear-gradient(180deg, #0a2444 0%, #081c33 100%);
}
.header {
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(80, 140, 200, 0.3);
}
.title {
  font-size: 32px;
  letter-spacing: 6px;
  color: #e8f4ff;
  margin: 0;
  text-shadow: 0 0 24px rgba(56, 189, 248, 0.55);
}
.header-side {
  width: 320px;
  color: #9fb8d0;
}
.header-side.right {
  text-align: right;
}
.clock {
  font-size: 18px;
  color: #9fd4ff;
  letter-spacing: 1px;
}
.badge {
  border: 1px solid rgba(56, 189, 248, 0.5);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  letter-spacing: 2px;
  color: #38bdf8;
}
.kpi-row {
  display: flex;
  gap: 20px;
  margin-top: 16px;
}
.kpi-card {
  flex: 1;
  height: 118px;
  background: rgba(20, 55, 95, 0.45);
  border: 1px solid rgba(80, 140, 200, 0.28);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.kpi-icon {
  display: flex;
  align-items: baseline;
  gap: 4px;
  border-bottom: 2px solid;
  padding-bottom: 4px;
}
.kpi-num {
  font-size: 40px;
  font-weight: 700;
  color: #eaf6ff;
}
.kpi-unit {
  font-size: 13px;
  color: #9fb8d0;
}
.kpi-label {
  margin-top: 8px;
  color: #9fb8d0;
  font-size: 14px;
  letter-spacing: 2px;
}
.charts-row {
  flex: 1;
  display: flex;
  gap: 20px;
  margin-top: 16px;
}
.col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.panel {
  background: rgba(20, 55, 95, 0.4);
  border: 1px solid rgba(80, 140, 200, 0.28);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
}
.panel-title {
  color: #cfe8ff;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 2px;
  border-left: 4px solid #38bdf8;
  padding-left: 10px;
  margin-bottom: 6px;
}
.panel-body {
  flex: 1;
  min-height: 0;
}
.chart {
  width: 100%;
  height: 245px;
}
.map-chart {
  height: 545px;
}
.legend-bar {
  display: flex;
  justify-content: center;
  gap: 18px;
  padding: 4px 0 0;
}
.legend-item {
  color: #9fb8d0;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-item i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.footer {
  text-align: center;
  color: #6d89a5;
  font-size: 13px;
  padding-top: 8px;
}
.degrade-mask {
  position: absolute;
  inset: 0;
  background: rgba(4, 16, 30, 0.86);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.degrade-card {
  text-align: center;
  color: #cfe3f5;
}
.degrade-card h2 {
  color: #f5f9ff;
  margin: 16px 0 8px;
}
.degrade-card p {
  color: #9fb8d0;
  margin-bottom: 22px;
}
</style>
