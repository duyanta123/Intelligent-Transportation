/**
 * Webster 配时计算（前端预览版，与后端 app/services/algorithms.py 保持一致）
 * 参数遵循《智慧交通-项目开发Prompt.md》附录 D.2
 */
export const SATURATION_FLOW = 1800
export const LOSS_PER_PHASE = 6
export const CYCLE_MIN = 40
export const CYCLE_MAX = 180
export const MIN_GREEN = 15

export interface WebsterPhaseInput {
  name: string
  flow: number
  lanes: number
}

export interface WebsterResult {
  cycle_seconds: number
  total_lost: number
  y_sum: number
  oversaturated: boolean
  phases: { name: string; green: number; y: number }[]
}

export function websterCalc(phases: WebsterPhaseInput[]): WebsterResult {
  if (phases.length === 0) {
    throw new Error('至少需要一个相位')
  }
  const yList = phases.map((p) => {
    if (p.flow <= 0) throw new Error(`相位[${p.name}]车流量必须大于 0`)
    if (p.lanes <= 0) throw new Error(`相位[${p.name}]车道数必须大于 0`)
    return p.flow / (SATURATION_FLOW * p.lanes)
  })
  const ySum = yList.reduce((a, b) => a + b, 0)
  const totalLost = phases.length * LOSS_PER_PHASE
  const oversaturated = ySum >= 0.95
  let cycle: number
  if (oversaturated) {
    cycle = CYCLE_MAX
  } else {
    cycle = (1.5 * totalLost + 5) / (1 - ySum)
    cycle = Math.max(CYCLE_MIN, Math.min(CYCLE_MAX, cycle))
  }
  const available = cycle - totalLost
  let greens: number[]
  if (available < MIN_GREEN * phases.length) {
    greens = phases.map(() => MIN_GREEN)
  } else {
    greens = yList.map((y) => (available * y) / ySum)
    for (let iter = 0; iter < 10; iter++) {
      const low = greens.map((g, i) => (g < MIN_GREEN - 1e-9 ? i : -1)).filter((i) => i >= 0)
      if (low.length === 0) break
      const deficit = low.reduce((sum, i) => sum + (MIN_GREEN - greens[i]), 0)
      low.forEach((i) => (greens[i] = MIN_GREEN))
      const high = greens.map((g, i) => (low.includes(i) ? -1 : i)).filter((i) => i >= 0)
      const highTotal = high.reduce((sum, i) => sum + greens[i], 0)
      if (high.length === 0 || highTotal <= 0) break
      high.forEach((i) => (greens[i] -= (deficit * greens[i]) / highTotal))
    }
  }
  greens = greens.map((g) => Math.max(MIN_GREEN, Math.round(g)))
  // 取整可能超出钳制周期：从最大相位扣减（不低于最短绿灯）
  const limit = Math.min(CYCLE_MAX, cycle) - totalLost
  while (greens.reduce((a, b) => a + b, 0) > limit) {
    const idx = greens.indexOf(Math.max(...greens))
    if (greens[idx] <= MIN_GREEN) break
    greens[idx] -= 1
  }
  return {
    cycle_seconds: greens.reduce((a, b) => a + b, 0) + totalLost,
    total_lost: totalLost,
    y_sum: Math.round(ySum * 10000) / 10000,
    oversaturated,
    phases: phases.map((p, i) => ({ name: p.name, green: greens[i], y: Math.round(yList[i] * 10000) / 10000 })),
  }
}

/**
 * 停车计费估算（前端展示用，与后端 algorithms.calc_parking_fee 保持一致）
 */
export function estimateParkingFee(
  minutes: number,
  freeMinutes: number,
  firstHourFee: number,
  hourlyFee: number,
  dailyCap: number,
): number {
  if (minutes <= 0) return 0
  const fullDays = Math.floor(minutes / 1440)
  const remainder = minutes - fullDays * 1440
  let fee = fullDays * dailyCap
  if (remainder > freeMinutes) {
    const billableHours = Math.ceil((remainder - freeMinutes) / 60)
    fee += Math.min(firstHourFee + (billableHours - 1) * hourlyFee, dailyCap)
  }
  return Math.round(fee * 100) / 100
}
