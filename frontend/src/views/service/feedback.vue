<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px">
          <el-option v-for="(name, key) in statusNames" :key="key" :label="name" :value="key" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <span class="spacer" />
        <el-button type="success" :icon="EditPen" @click="submitVisible = true">提交反馈</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.title || '（无标题）' }}</template>
        </el-table-column>
        <el-table-column prop="content" label="内容" min-width="240" show-overflow-tooltip />
        <el-table-column prop="reply" label="处理答复" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.reply || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'resolved' ? 'success' : row.status === 'processing' ? 'primary' : 'warning'">{{ row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="170" />
        <el-table-column v-if="canHandle" label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status !== 'resolved'" text type="primary" @click="openHandle(row)">受理处理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next" class="pager" @current-change="load" />
    </el-card>

    <!-- 提交反馈 -->
    <el-dialog v-model="submitVisible" title="提交投诉反馈" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="70px">
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="128" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="5" placeholder="请描述问题（5-2000 字）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="submitVisible = false">取消</el-button>
        <el-button type="primary" @click="doSubmit">提交</el-button>
      </template>
    </el-dialog>

    <!-- 受理处理 -->
    <el-dialog v-model="handleVisible" title="受理处理" width="480px">
      <el-form label-width="80px">
        <el-form-item label="反馈内容">
          <div class="handle-content">{{ handling?.content }}</div>
        </el-form-item>
        <el-form-item label="状态" required>
          <el-radio-group v-model="handleForm.status">
            <el-radio value="processing">处理中</el-radio>
            <el-radio value="resolved">已办结</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="答复" required>
          <el-input v-model="handleForm.reply" type="textarea" :rows="3" placeholder="填写答复内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible = false">取消</el-button>
        <el-button type="primary" @click="doHandle">提交处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Search, EditPen } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { fetchFeedbacks, submitFeedback, handleFeedback } from '@/api/service'
import type { Feedback } from '@/api/service'
import { sequenceGuard } from '@/utils/async'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canHandle = computed(() => auth.role === 'admin' || auth.role === 'officer')
const statusNames: Record<string, string> = { pending: '待受理', processing: '处理中', resolved: '已办结' }

const rows = ref<Feedback[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const listSeq = sequenceGuard()
const query = reactive({ status: '' })

const submitVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ title: '', content: '' })
const rules: FormRules = {
  content: [
    { required: true, message: '请输入反馈内容', trigger: 'blur' },
    { min: 5, message: '至少 5 个字', trigger: 'blur' },
  ],
}

const handleVisible = ref(false)
const handling = ref<Feedback | null>(null)
const handleForm = reactive({ status: 'processing', reply: '' })

async function load() {
  const seq = listSeq.begin()
  loading.value = true
  try {
    const { data } = await fetchFeedbacks({ page: page.value, size: size.value, status: query.status })
    if (listSeq.isCurrent(seq)) {
      rows.value = data.list
      total.value = data.total
    }
  } finally {
    if (listSeq.isCurrent(seq)) loading.value = false
  }
}

/** 条件查询：重置到第 1 页，避免停在深层页码查不到数据 */
function search() {
  page.value = 1
  load()
}

async function doSubmit() {
  await formRef.value?.validate()
  await submitFeedback({ ...form })
  ElMessage.success('提交成功，等待受理')
  submitVisible.value = false
  Object.assign(form, { title: '', content: '' })
  await load()
}

function openHandle(row: Feedback) {
  handling.value = row
  // 只有"已办结"默认保持办结；待受理/处理中都默认进"处理中"（此前处理中的反馈会被默认成已办结）
  handleForm.status = row.status === 'resolved' ? 'resolved' : 'processing'
  handleForm.reply = row.reply ?? ''
  handleVisible.value = true
}

async function doHandle() {
  if (!handling.value) return
  if (handleForm.reply.trim().length < 2) {
    ElMessage.warning('请填写答复内容')
    return
  }
  await handleFeedback(handling.value.id, { ...handleForm })
  ElMessage.success('处理成功')
  handleVisible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
.handle-content {
  color: #606266;
  line-height: 1.6;
  max-height: 120px;
  overflow: auto;
}
</style>
