<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>运行状态</h2>
        <div class="header-actions">
          <el-tag :type="overallStatus.type">{{ overallStatus.text }}</el-tag>
          <el-button :loading="loading" @click="refresh">刷新</el-button>
        </div>
      </div>
      <div class="summary-grid status-summary">
        <div class="metric">
          API 存活
          <strong>{{ live.status }}</strong>
          <span>{{ live.detail }}</span>
        </div>
        <div class="metric">
          API 就绪
          <strong>{{ ready.status }}</strong>
          <span>{{ ready.detail }}</span>
        </div>
        <div class="metric">
          数据质量
          <strong>{{ qualityStatus?.status ?? '-' }}</strong>
          <span>错误 {{ qualityStatus?.error_logs ?? 0 }} / 警告 {{ qualityStatus?.warning_logs ?? 0 }}</span>
        </div>
        <div class="metric">
          最近任务
          <strong>{{ failedTaskCount }}</strong>
          <span>失败或取消任务</span>
        </div>
      </div>
    </section>

    <section class="panel span-5">
      <div class="panel-header">
        <h2>服务探针</h2>
      </div>
      <el-table :data="healthRows" height="300">
        <el-table-column prop="name" label="检查项" width="120" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.ok ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="说明" min-width="180" />
      </el-table>
    </section>

    <section class="panel span-7">
      <div class="panel-header">
        <h2>最近后台任务</h2>
        <el-button text @click="refreshTasks">刷新任务</el-button>
      </div>
      <el-table :data="tasks" height="300">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="taskTagType(row.status)">{{ taskStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="current_step" label="当前步骤" width="130" />
        <el-table-column prop="created_at" label="创建时间" min-width="170" />
        <el-table-column prop="error_message" label="错误" min-width="220" />
      </el-table>
    </section>

    <section class="panel span-12">
      <div class="panel-header">
        <h2>数据质量日志</h2>
        <el-tag :type="qualityTagType">{{ qualityStatus?.status ?? '未知' }}</el-tag>
      </div>
      <el-table :data="qualityLogs" height="360">
        <el-table-column prop="created_at" label="创建时间" width="190" />
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="trade_date" label="日期" width="130" />
        <el-table-column prop="check_type" label="检查项" width="180" />
        <el-table-column label="级别" width="110">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="280" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchDataQualityLogs,
  fetchDataQualityStatus,
  fetchHealth,
  fetchLiveHealth,
  fetchReadyHealth,
  fetchWorkflowTasks,
  type DataQualityLog,
  type DataQualityStatus,
  type HealthStatus,
  type WorkflowTask,
} from '../api/client'

type TagType = 'success' | 'warning' | 'danger' | 'info'

interface ProbeState {
  ok: boolean
  status: string
  detail: string
}

const loading = ref(true)
const health = ref<ProbeState>(emptyProbe())
const live = ref<ProbeState>(emptyProbe())
const ready = ref<ProbeState>(emptyProbe())
const qualityStatus = ref<DataQualityStatus>()
const qualityLogs = ref<DataQualityLog[]>([])
const tasks = ref<WorkflowTask[]>([])

onMounted(refresh)

const healthRows = computed(() => [
  { name: 'health', ...health.value },
  { name: 'live', ...live.value },
  { name: 'ready', ...ready.value },
])

const failedTaskCount = computed(() => tasks.value.filter((task) => ['failed', 'cancelled'].includes(task.status)).length)

const qualityTagType = computed<TagType>(() => {
  if (!qualityStatus.value) return 'info'
  if (qualityStatus.value.error_logs > 0) return 'danger'
  if (qualityStatus.value.warning_logs > 0) return 'warning'
  return 'success'
})

const overallStatus = computed<{ type: TagType; text: string }>(() => {
  if (!health.value.ok || !live.value.ok || !ready.value.ok) return { type: 'danger', text: '服务异常' }
  if (qualityStatus.value?.error_logs || failedTaskCount.value > 0) return { type: 'warning', text: '需要关注' }
  return { type: 'success', text: '运行正常' }
})

async function refresh() {
  loading.value = true
  try {
    const [healthResult, liveResult, readyResult, qualityResult, logsResult, tasksResult] = await Promise.allSettled([
      fetchHealth(),
      fetchLiveHealth(),
      fetchReadyHealth(),
      fetchDataQualityStatus(),
      fetchDataQualityLogs(),
      fetchWorkflowTasks(),
    ])
    health.value = toProbeState(healthResult, '基础健康检查')
    live.value = toProbeState(liveResult, 'API 进程存活')
    ready.value = toProbeState(readyResult, '数据库与 worker 就绪')
    if (qualityResult.status === 'fulfilled') qualityStatus.value = qualityResult.value
    if (logsResult.status === 'fulfilled') qualityLogs.value = logsResult.value
    if (tasksResult.status === 'fulfilled') tasks.value = tasksResult.value
  } finally {
    loading.value = false
  }
}

async function refreshTasks() {
  tasks.value = await fetchWorkflowTasks()
}

function toProbeState(result: PromiseSettledResult<HealthStatus>, fallback: string): ProbeState {
  if (result.status === 'fulfilled') {
    const mode = result.value.workflow_execution_mode ? `，工作流模式 ${result.value.workflow_execution_mode}` : ''
    return {
      ok: true,
      status: result.value.status,
      detail: `${result.value.service} / ${result.value.environment}${mode}`,
    }
  }
  const message = result.reason?.response?.data?.detail || result.reason?.message || fallback
  return { ok: false, status: '异常', detail: String(message) }
}

function emptyProbe(): ProbeState {
  return { ok: false, status: '-', detail: '-' }
}

function taskStatusText(status: string) {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status] || status
}

function taskTagType(status: string): TagType {
  if (status === 'success') return 'success'
  if (status === 'running' || status === 'pending') return 'warning'
  if (status === 'failed' || status === 'cancelled') return 'danger'
  return 'info'
}

function severityTagType(severity: string): TagType {
  if (severity === 'error') return 'danger'
  if (severity === 'warning') return 'warning'
  if (severity === 'info') return 'info'
  return 'success'
}
</script>
