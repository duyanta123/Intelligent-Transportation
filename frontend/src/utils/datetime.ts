/**
 * 本地时间格式化：替代 toISOString()（UTC，+8 时区下会差 8 小时）
 * 全链路约定 Asia/Shanghai 本地时间（见 AGENTS.md 第 5 节）
 */

const pad = (n: number) => String(n).padStart(2, '0')

/** 当前本地时间 "YYYY-MM-DD HH:mm:ss" */
export function nowLocalString(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 当前本地日期 "YYYY-MM-DD"（导出文件名用） */
export function todayLocalDate(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
