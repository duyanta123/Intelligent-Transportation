/** utils/datetime 与 utils/async 的单元测试（审查修复的配套工具） */
import { describe, expect, it } from 'vitest'
import { nowLocalString, todayLocalDate } from '@/utils/datetime'
import { sequenceGuard } from '@/utils/async'

describe('datetime 工具', () => {
  it('nowLocalString 返回本地时间且与 Date 各分量一致', () => {
    const before = new Date()
    const s = nowLocalString()
    const after = new Date()
    expect(s).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
    // 修复点：与 toISOString 不同，小时必须等于本地小时（而非 UTC）
    expect(Number(s.slice(11, 13))).toBeGreaterThanOrEqual(before.getHours() === after.getHours() ? before.getHours() : Math.min(before.getHours(), after.getHours()))
    expect(Number(s.slice(11, 13))).toBeLessThanOrEqual(after.getHours())
    expect(s.slice(0, 10)).toBe(`${before.getFullYear()}-${String(before.getMonth() + 1).padStart(2, '0')}-${String(before.getDate()).padStart(2, '0')}`)
  })

  it('todayLocalDate 返回本地日期 YYYY-MM-DD', () => {
    const d = new Date()
    const expected = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    expect(todayLocalDate()).toBe(expected)
    // 导出文件名用法：无冒号空格
    expect(todayLocalDate()).not.toMatch(/[: ]/)
  })
})

describe('sequenceGuard 请求竞态防护', () => {
  it('begin 递增序号，isCurrent 只认最新一次', () => {
    const guard = sequenceGuard()
    const a = guard.begin()
    expect(guard.isCurrent(a)).toBe(true)
    const b = guard.begin()
    expect(guard.isCurrent(a)).toBe(false) // 旧请求应丢弃
    expect(guard.isCurrent(b)).toBe(true)
  })

  it('互不干扰的多个 guard 实例', () => {
    const g1 = sequenceGuard()
    const g2 = sequenceGuard()
    const a = g1.begin()
    g2.begin()
    expect(g1.isCurrent(a)).toBe(true)
  })
})
