<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>系统角色（RBAC：角色-菜单-权限三级控制）</template>
      <el-table :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="code" label="角色编码" width="140">
          <template #default="{ row }">
            <el-tag :type="{ admin: 'danger', officer: 'warning', user: 'success' }[row.code] ?? 'info'">{{ row.code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="角色名称" width="180" />
        <el-table-column prop="description" label="描述" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchRoles } from '@/api/auth'

const rows = ref<Record<string, unknown>[]>([])
onMounted(async () => {
  const { data } = await fetchRoles()
  rows.value = data
})
</script>
