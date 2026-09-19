<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-toolbar">
        <span class="hint">菜单树对应前端路由与权限（admin 全部可见，officer/user 由角色-菜单关联决定）</span>
        <span class="spacer" />
        <el-button type="primary" :icon="Plus" @click="openCreate()">新增菜单</el-button>
      </div>
      <el-table v-loading="loading" :data="treeRows" row-key="id" :tree-props="{ children: 'children' }" stripe default-expand-all>
        <el-table-column prop="name" label="菜单名称" min-width="160" />
        <el-table-column prop="path" label="路由路径" min-width="170" />
        <el-table-column prop="component" label="组件" min-width="200" show-overflow-tooltip />
        <el-table-column prop="icon" label="图标" width="120" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.menu_type === 0 ? 'warning' : 'success'">{{ row.menu_type === 0 ? '目录' : '菜单' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button text type="primary" @click="openCreate(row)">子菜单</el-button>
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑菜单' : '新增菜单'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="父菜单">
          <el-select v-model="form.parent_id" style="width: 100%">
            <el-option label="顶级菜单" :value="0" />
            <el-option v-for="m in topMenus" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="路由路径">
          <el-input v-model="form.path" placeholder="如 /system/users" />
        </el-form-item>
        <el-form-item label="组件">
          <el-input v-model="form.component" placeholder="如 views/system/users.vue" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="Element Plus 图标名" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.menu_type">
            <el-radio :value="0">目录</el-radio>
            <el-radio :value="1">菜单</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchMenus, createMenu, updateMenu, deleteMenu } from '@/api/auth'
import type { MenuItem } from '@/types/api'

const rows = ref<MenuItem[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(0)
const form = reactive({ parent_id: 0, name: '', path: '', component: '', icon: '', menu_type: 1, sort_order: 0 })

interface MenuNode extends MenuItem {
  children?: MenuNode[]
}

function buildTree(list: MenuItem[], parentId = 0): MenuNode[] {
  return list
    .filter((m) => m.parent_id === parentId)
    .map((m) => {
      const children = buildTree(list, m.id)
      return children.length ? { ...m, children } : { ...m }
    })
}

const treeRows = computed(() => buildTree(rows.value))
const topMenus = computed(() => rows.value.filter((m) => m.parent_id === 0))

async function load() {
  loading.value = true
  try {
    const { data } = await fetchMenus()
    rows.value = data
  } finally {
    loading.value = false
  }
}

function openCreate(parent?: MenuItem) {
  editingId.value = 0
  Object.assign(form, { parent_id: parent?.id ?? 0, name: '', path: '', component: '', icon: 'Menu', menu_type: 1, sort_order: 0 })
  dialogVisible.value = true
}

function openEdit(row: MenuItem) {
  editingId.value = row.id
  Object.assign(form, { parent_id: row.parent_id, name: row.name, path: row.path, component: row.component, icon: row.icon, menu_type: row.menu_type, sort_order: row.sort_order })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入菜单名称')
    return
  }
  if (editingId.value) {
    await updateMenu(editingId.value, { ...form })
  } else {
    await createMenu({ ...form })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await load()
}

async function remove(row: MenuItem) {
  await ElMessageBox.confirm(`确认删除菜单「${row.name}」？`, '提示', { type: 'warning' })
  await deleteMenu(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint {
  color: #909399;
  font-size: 13px;
}
</style>
