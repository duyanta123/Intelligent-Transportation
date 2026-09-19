import { describe, it, expect } from 'vitest'
import { websterCalc, estimateParkingFee } from '@/utils/algorithms'

describe('配时计算（Webster，与后端 algorithms.py 同源）', () => {
  it('周期落在 [40, 180] 秒钳制区间内', () => {
    const result = websterCalc([
      { name: '南北直行', flow: 800, lanes: 2 },
      { name: '东西直行', flow: 600, lanes: 2 },
    ])
    expect(result.cycle_seconds).toBeGreaterThanOrEqual(40)
    expect(result.cycle_seconds).toBeLessThanOrEqual(180)
    expect(result.oversaturated).toBe(false)
  })

  it('总损失 = 相位数 × 6 秒', () => {
    const result = websterCalc([
      { name: 'A', flow: 900, lanes: 2 },
      { name: 'B', flow: 700, lanes: 2 },
      { name: 'C', flow: 500, lanes: 1 },
    ])
    expect(result.total_lost).toBe(18)
  })

  it('绿灯按流量比分配：流量越大绿灯越长', () => {
    const result = websterCalc([
      { name: '主', flow: 2400, lanes: 2 },
      { name: '次', flow: 600, lanes: 2 },
    ])
    expect(result.phases[0].green).toBeGreaterThan(result.phases[1].green * 2)
  })

  it('最短绿灯 15 秒约束', () => {
    const result = websterCalc([
      { name: '主', flow: 1500, lanes: 2 },
      { name: '次', flow: 30, lanes: 1 },
    ])
    for (const phase of result.phases) {
      expect(phase.green).toBeGreaterThanOrEqual(15)
    }
  })

  it('过饱和（Y≥0.95）按上限 180 秒输出', () => {
    const result = websterCalc([
      { name: 'A', flow: 3000, lanes: 2 },
      { name: 'B', flow: 3200, lanes: 2 },
    ])
    expect(result.oversaturated).toBe(true)
    expect(result.cycle_seconds).toBe(180)
  })

  it('拒绝非法输入', () => {
    expect(() => websterCalc([])).toThrow()
    expect(() => websterCalc([{ name: 'A', flow: 0, lanes: 1 }])).toThrow()
  })
})

describe('停车计费估算（与后端 calc_parking_fee 同源）', () => {
  it('免费时长内 0 元', () => {
    expect(estimateParkingFee(14, 15, 5, 3, 40)).toBe(0)
  })

  it('首小时计费', () => {
    // 65 分钟，免费 15 → 1 小时 → 5 元
    expect(estimateParkingFee(65, 15, 5, 3, 40)).toBe(5)
  })

  it('不足 1 小时按 1 小时', () => {
    // 76 分钟，免费 15 → 61 分钟 → 2 小时 → 5+3 = 8 元
    expect(estimateParkingFee(76, 15, 5, 3, 40)).toBe(8)
  })

  it('单日封顶', () => {
    expect(estimateParkingFee(1200, 0, 5, 3, 40)).toBe(40)
  })

  it('跨天按 24 小时分段计费', () => {
    // 2 整天 + 1 小时：2*40 + 5 = 85
    expect(estimateParkingFee(1440 * 2 + 60, 0, 5, 3, 40)).toBe(85)
  })
})
