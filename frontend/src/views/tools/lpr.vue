<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>车牌识别（HyperLPR3 · CPU 推理）——识别结果可一键填入出入场/违章表单</template>
      <el-row :gutter="20">
        <el-col :span="10">
          <el-upload
            drag
            :auto-upload="false"
            :show-file-list="false"
            accept=".jpg,.jpeg,.png,.webp"
            :on-change="onFileChange"
          >
            <el-icon :size="42"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽车辆图片到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">仅支持 jpg / png / webp，不超过 5MB</div>
            </template>
          </el-upload>
          <el-image v-if="previewUrl" :src="previewUrl" fit="contain" class="preview" />
        </el-col>
        <el-col :span="14">
          <el-result
            v-if="result"
            icon="success"
            title="识别完成"
            :sub-title="`车牌号：${result.plate_no}，置信度：${(result.confidence * 100).toFixed(1)}%`"
          >
            <template #extra>
              <el-space wrap>
                <el-button type="primary" @click="copyResult">复制车牌号</el-button>
                <el-button type="success" @click="fillEnter">填入入场表单</el-button>
                <el-button type="warning" @click="fillViolation">填入违章表单</el-button>
              </el-space>
            </template>
          </el-result>
          <el-result v-else-if="failed" icon="warning" title="识别失败" sub-title="模型不可用或未识别到车牌，请手动录入车牌号（降级路径）">
            <template #extra>
              <el-input v-model="manualPlate" placeholder="手动录入车牌号" style="width: 240px">
                <template #append>
                  <el-button @click="copyResult">复制</el-button>
                </template>
              </el-input>
            </template>
          </el-result>
          <el-empty v-else description="上传图片后点击「开始识别」" />
          <div style="margin-top: 14px; display: flex; gap: 12px">
            <el-button type="primary" size="large" :loading="loading" :disabled="!selectedFile" @click="doRecognize">开始识别</el-button>
            <el-button v-if="failed" size="large" @click="failed = false">重新上传</el-button>
          </div>
          <el-alert class="note" type="info" :closable="false" title="首次调用会自动下载识别模型（约 10MB），下载完成后缓存在本机；若网络受限将自动走「手动录入」降级路径。" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { recognizePlate } from '@/api/dashboard'

const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const result = ref<{ plate_no: string; confidence: number } | null>(null)
const failed = ref(false)
const manualPlate = ref('')
const loading = ref(false)

function onFileChange(file: { raw?: File }) {
  if (!file.raw) return
  if (file.raw.size > 5 * 1024 * 1024) {
    ElMessage.error('图片不能超过 5MB')
    return
  }
  selectedFile.value = file.raw
  // 释放旧预览的 Blob，避免多次换图后内存持续驻留
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(file.raw)
  result.value = null
  failed.value = false
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

async function doRecognize() {
  if (!selectedFile.value) return
  loading.value = true
  failed.value = false
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    const { data } = await recognizePlate(fd)
    result.value = data
  } catch {
    // 降级路径：模型不可用/超时 → 手动录入
    result.value = null
    failed.value = true
  } finally {
    loading.value = false
  }
}

function copyResult() {
  const text = result.value?.plate_no ?? manualPlate.value
  if (!text) return
  navigator.clipboard.writeText(text)
  ElMessage.success(`已复制：${text}`)
}

function fillEnter() {
  ElMessage.info('已复制车牌号，请到「出入场记录 → 车辆入场」粘贴使用')
  copyResult()
}

function fillViolation() {
  ElMessage.info('已复制车牌号，请到「违章管理 → 录入违章」粘贴使用')
  copyResult()
}
</script>

<style scoped>
.preview {
  margin-top: 14px;
  width: 100%;
  max-height: 260px;
  border-radius: 8px;
  background: #f5f7fa;
}
.note {
  margin-top: 16px;
}
</style>
