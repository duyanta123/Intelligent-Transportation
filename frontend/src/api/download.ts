/** 文件下载：blob 方式拉取（绕过 JSON 响应拦截器），带 token，浏览器端触发保存 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken } from './http'

export async function downloadFile(url: string, params: Record<string, unknown> = {}, filename: string): Promise<void> {
  try {
    const resp = await axios.get(`${import.meta.env.VITE_API_BASE || '/api/v1'}${url}`, {
      params,
      responseType: 'blob',
      timeout: 60000,
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const blob = new Blob([resp.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    ElMessage.success(`已导出：${filename}`)
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  }
}
