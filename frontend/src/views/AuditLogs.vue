<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>操作审计</h2>
          <p class="section-note">记录 POST、PATCH、DELETE 等变更类接口调用，不保存请求正文和密钥。</p>
        </div>
        <div class="header-actions">
          <el-input v-model="filters.actor_username" placeholder="操作者" clearable class="symbol-input" />
          <el-input v-model="filters.action" placeholder="动作" clearable class="symbol-input" />
          <el-button :loading="loading" @click="loadLogs">刷新</el-button>
        </div>
      </div>
      <div class="summary-grid task-summary">
        <div class="metric">日志数<strong>{{ logs.length }}</strong><span>最近 {{ filters.limit }} 条</span></div>
        <div class="metric">异常数<strong>{{ errorCount }}</strong><span>HTTP 400 及以上</span></div>
        <div class="metric">最近操作者<strong>{{ latestActor }}</strong><span>来自最近一条审计</span></div>
        <div class="metric">最近动作<strong>{{ latestAction }}</strong><span>仅记录变更类请求</span></div>
      </div>
      <el-table :data="logs" height="620" size="small">
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="actor_username" label="操作者" width="120" />
        <el-table-column prop="actor_role" label="角色" width="90" />
        <el-table-column prop="method" label="方法" width="80" />
        <el-table-column prop="action" label="动作" width="140" />
        <el-table-column prop="path" label="路径" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status_code)">{{ row.status_code ?? '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">{{ row.duration_ms ?? '-' }} ms</template>
        </el-table-column>
        <el-table-column prop="client_ip" label="IP" width="130" />
        <el-table-column prop="request_id" label="Request ID" min-width="220" show-overflow-tooltip />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAuditLogs, type AuditLog } from '../api/client'

type TagType = 'success' | 'warning' | 'danger' | 'info'

const loading = ref(false)
const logs = ref<AuditLog[]>([])
const filters = reactive({
  limit: 100,
  actor_username: '',
  action: '',
})

const errorCount = computed(() => logs.value.filter((item) => (item.status_code ?? 0) >= 400).length)
const latestActor = computed(() => logs.value[0]?.actor_username || '-')
const latestAction = computed(() => logs.value[0]?.action || '-')

onMounted(loadLogs)

async function loadLogs() {
  loading.value = true
  try {
    logs.value = await fetchAuditLogs({
      limit: filters.limit,
      actor_username: filters.actor_username.trim() || undefined,
      action: filters.action.trim() || undefined,
    })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取审计日志失败')
  } finally {
    loading.value = false
  }
}

function statusTag(status?: number | null): TagType {
  if (!status) return 'info'
  if (status >= 500) return 'danger'
  if (status >= 400) return 'warning'
  return 'success'
}
</script>
