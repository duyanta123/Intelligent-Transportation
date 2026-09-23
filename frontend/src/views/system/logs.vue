<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <el-input v-model="username" placeholder="操作人" clearable style="width: 180px" />
        <el-select v-model="action" placeholder="操作类型" clearable style="width: 140px">
          <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="操作人" width="110" />
        <el-table-column prop="action" label="操作" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.action === '删除' ? 'danger' : row.action === '登录' ? 'info' : 'success'">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next, sizes" class="pager" @current-change="load" @size-change="load" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { fetchOpLogs } from '@/api/auth'
import { sequenceGuard } from '@/utils/async'

const rows = ref<Record<string, string>[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const username = ref('')
const action = ref('')
const loading = ref(false)
const listSeq = sequenceGuard()
const actions = ['登录', '登出', '注册', '改密', '新增', '修改', '删除', '审核', '发布', '受理', '录入', '上报', '识别', '入场', '出场', '处理', '计算', '反馈']

async function load() {
  const seq = listSeq.begin()
  loading.value = true
  try {
    const { data } = await fetchOpLogs({ page: page.value, size: size.value, username: username.value, action: action.value })
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

onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
