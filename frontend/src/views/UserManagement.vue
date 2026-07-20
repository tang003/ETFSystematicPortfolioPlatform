<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>用户管理</h2>
          <p class="section-note">管理可登录系统的数据库用户。当前环境变量管理员账号仍然保留，用于兜底登录。</p>
        </div>
        <div class="header-actions">
          <el-button @click="loadUsers">刷新</el-button>
          <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
        </div>
      </div>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="角色说明：admin 可管理数据源、策略和后台任务；researcher 用于后续投研操作权限；viewer 用于只读观察。"
      />
    </section>

    <section class="panel span-12">
      <el-table :data="users" height="520" empty-text="暂无数据库用户">
        <el-table-column prop="username" label="用户名" min-width="150" />
        <el-table-column prop="display_name" label="显示名称" min-width="140" />
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最近登录" min-width="180" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link :type="row.is_active ? 'warning' : 'success'" @click="toggleUser(row)">
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingUser ? '编辑用户' : '新增用户'" width="520px">
      <el-form label-position="top">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="Boolean(editingUser)" placeholder="例如 researcher01" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.display_name" placeholder="可选" />
        </el-form-item>
        <el-form-item :label="editingUser ? '新密码（留空不修改）' : '密码'" :required="!editingUser">
          <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="管理员 admin" value="admin" />
            <el-option label="研究员 researcher" value="researcher" />
            <el-option label="观察者 viewer" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createUser, fetchUsers, updateUser, type AppUser } from '../api/client'

const loading = ref(false)
const saving = ref(false)
const users = ref<AppUser[]>([])
const dialogVisible = ref(false)
const editingUser = ref<AppUser | null>(null)
const form = reactive({
  username: '',
  password: '',
  role: 'viewer',
  display_name: '',
  is_active: true,
})

onMounted(loadUsers)

async function loadUsers() {
  loading.value = true
  try {
    users.value = await fetchUsers({ limit: 200 })
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingUser.value = null
  Object.assign(form, { username: '', password: '', role: 'viewer', display_name: '', is_active: true })
  dialogVisible.value = true
}

function openEditDialog(row: AppUser) {
  editingUser.value = row
  Object.assign(form, {
    username: row.username,
    password: '',
    role: row.role,
    display_name: row.display_name || '',
    is_active: row.is_active,
  })
  dialogVisible.value = true
}

async function saveUser() {
  if (!form.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!editingUser.value && form.password.length < 12) {
    ElMessage.warning('新增用户密码至少 12 位')
    return
  }
  saving.value = true
  try {
    if (editingUser.value) {
      await updateUser(editingUser.value.username, {
        password: form.password || null,
        role: form.role,
        display_name: form.display_name || null,
        is_active: form.is_active,
      })
      ElMessage.success('用户已更新')
    } else {
      await createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        display_name: form.display_name || null,
        is_active: form.is_active,
      })
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    await loadUsers()
  } finally {
    saving.value = false
  }
}

async function toggleUser(row: AppUser) {
  await updateUser(row.username, { is_active: !row.is_active })
  ElMessage.success(row.is_active ? '用户已停用' : '用户已启用')
  await loadUsers()
}

function roleText(role: string) {
  const map: Record<string, string> = {
    admin: '管理员',
    researcher: '研究员',
    viewer: '观察者',
  }
  return map[role] || role
}

function roleTag(role: string) {
  if (role === 'admin') return 'danger'
  if (role === 'researcher') return 'warning'
  return 'info'
}
</script>
