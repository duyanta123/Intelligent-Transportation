/** 文件下载：走统一 http 实例（带 token 与 401 处理），blob 响应在拦截器中原样透传 */
import http from './http'
import { ElMessage } from 'element-plus'

export async function downloadFile(url: string, params: Record<string, unknown> = {}, filename: string): Promise<void> {
  try {
    const resp = await http.get(url, { params, responseType: 'blob', timeout: 60000 })
    const blob = new Blob([resp.data as BlobPart])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    ElMessage.success(`已导出：${filename}`)
  } catch {
    // 错误提示已由 http 拦截器统一弹出（含 401 跳登录），此处不再重复
  }
}
