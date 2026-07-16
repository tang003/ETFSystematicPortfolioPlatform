<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>运行状态</h2>
        <div class="header-actions">
          <el-tag :type="overallStatus.type">{{ overallStatus.text }}</el-tag>
          <el-tag type="info">自动刷新 {{ autoRefreshSeconds }}s</el-tag>
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
          后台任务
          <strong>{{ activeTaskCount }}</strong>
          <span>等待或执行中，异常 {{ failedTaskCount }}；{{ lastRefreshText }}</span>
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
        <h2>每日自动维护</h2>
        <div class="header-actions">
          <el-tag :type="maintenanceTagType">{{ maintenanceStatusText }}</el-tag>
          <el-button :loading="maintenanceRunning" :disabled="maintenance?.lock_active" @click="triggerMaintenance">
            立即执行
          </el-button>
        </div>
      </div>
      <div class="summary-grid task-summary">
        <div class="metric">
          执行时间
          <strong>{{ maintenanceTime }}</strong>
          <span>{{ maintenance?.timezone ?? 'Asia/Shanghai' }}</span>
        </div>
        <div class="metric">
          同步范围
          <strong>{{ scopeText(maintenance?.scope) }}</strong>
          <span>最多 {{ maintenance?.max_symbols ?? '-' }} 只 ETF</span>
        </div>
        <div class="metric">
          请求间隔
          <strong>{{ maintenance?.request_interval_seconds ?? '-' }}s</strong>
          <span>用于控制 Tushare 频率</span>
        </div>
        <div class="metric">
          最近结果
          <strong>{{ lastMaintenanceStatus }}</strong>
          <span>{{ lastMaintenanceDetail }}</span>
        </div>
      </div>

      <div v-if="latestMaintenanceCards.length" class="result-card-grid">
        <div v-for="card in latestMaintenanceCards" :key="card.title" class="result-card">
          <span>{{ card.title }}</span>
          <strong>{{ card.value }}</strong>
          <p>{{ card.detail }}</p>
        </div>
      </div>

      <el-alert
        v-if="maintenance?.lock_active"
        type="warning"
        show-icon
        :closable="false"
        title="每日维护正在执行中，请等待当前任务完成后再手动触发。"
      />
      <p class="section-note">
        每日维护只更新本地行情、因子、策略、风控、调仓建议和报告，不连接券商，不自动下单。
      </p>
    </section>

    <section class="panel span-12">
      <div class="panel-header">
        <h2>任务中心</h2>
        <div class="header-actions">
          <el-tag v-if="activeTaskCount > 0" type="warning">有任务运行中</el-tag>
          <el-button text @click="refreshTasks">刷新任务</el-button>
        </div>
      </div>
      <div class="summary-grid task-summary">
        <div class="metric">等待/执行<strong>{{ activeTaskCount }}</strong></div>
        <div class="metric">成功<strong>{{ successTaskCount }}</strong></div>
        <div class="metric">异常<strong>{{ failedTaskCount }}</strong></div>
      </div>
      <el-table :data="tasks" height="440">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="task-detail">
              <div class="task-detail-meta">
                <span>任务类型：{{ taskTypeText(row.task_type) }}</span>
                <span>耗时：{{ taskDuration(row) }}</span>
                <span>处理对象：{{ taskTargetSummary(row) }}</span>
              </div>
              <div v-if="taskResultCards(row).length" class="result-card-grid task-result-grid">
                <div v-for="card in taskResultCards(row)" :key="card.title" class="result-card">
                  <span>{{ card.title }}</span>
                  <strong>{{ card.value }}</strong>
                  <p>{{ card.detail }}</p>
                </div>
              </div>
              <el-table :data="row.steps" size="small">
                <el-table-column prop="step_name" label="步骤" width="150" />
                <el-table-column label="状态" width="100">
                  <template #default="{ row: step }">
                    <el-tag :type="taskTagType(step.status)">{{ taskStatusText(step.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="耗时" width="110">
                  <template #default="{ row: step }">{{ stepDuration(step) }}</template>
                </el-table-column>
                <el-table-column label="说明" min-width="320">
                  <template #default="{ row: step }">
                    {{ userFriendlyMessage(step.message) || summarizeStepPayload(step.result_payload) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="类型" width="130">
          <template #default="{ row }">{{ taskTypeText(row.task_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="taskTagType(row.status)">{{ taskStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="taskProgress(row)" :status="progressStatus(row.status)" />
          </template>
        </el-table-column>
        <el-table-column label="当前步骤" width="130">
          <template #default="{ row }">{{ currentStepName(row) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="110">
          <template #default="{ row }">{{ taskDuration(row) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="提示" min-width="260">
          <template #default="{ row }">{{ taskHint(row) }}</template>
        </el-table-column>
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
            <el-tag :type="severityTagType(row.severity)">{{ severityText(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="280" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  fetchDataQualityLogs,
  fetchDataQualityStatus,
  fetchHealth,
  fetchLiveHealth,
  fetchMaintenanceStatus,
  fetchReadyHealth,
  fetchWorkflowTasks,
  runMaintenanceNow,
  type DataQualityLog,
  type DataQualityStatus,
  type HealthStatus,
  type MaintenanceStatus,
  type WorkflowTask,
} from '../api/client'

type TagType = 'success' | 'warning' | 'danger' | 'info'

interface ProbeState {
  ok: boolean
  status: string
  detail: string
}

interface ResultCard {
  title: string
  value: string
  detail: string
}

const loading = ref(true)
const health = ref<ProbeState>(emptyProbe())
const live = ref<ProbeState>(emptyProbe())
const ready = ref<ProbeState>(emptyProbe())
const qualityStatus = ref<DataQualityStatus>()
const qualityLogs = ref<DataQualityLog[]>([])
const tasks = ref<WorkflowTask[]>([])
const maintenance = ref<MaintenanceStatus>()
const maintenanceRunning = ref(false)
const lastRefreshedAt = ref<Date | null>(null)
const autoRefreshSeconds = 15
let autoRefreshTimer: number | undefined

onMounted(() => {
  refresh()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

const healthRows = computed(() => [
  { name: 'health', ...health.value },
  { name: 'live', ...live.value },
  { name: 'ready', ...ready.value },
])

const failedTaskCount = computed(() => tasks.value.filter((task) => ['failed', 'cancelled'].includes(task.status)).length)
const activeTaskCount = computed(() => tasks.value.filter((task) => ['pending', 'running'].includes(task.status)).length)
const successTaskCount = computed(() => tasks.value.filter((task) => ['success', 'partial_success'].includes(task.status)).length)

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

const maintenanceTagType = computed<TagType>(() => {
  if (!maintenance.value) return 'info'
  if (maintenance.value.lock_active) return 'warning'
  if (!maintenance.value.enabled) return 'info'
  if (maintenance.value.last_run?.status === 'failed') return 'danger'
  return 'success'
})

const maintenanceStatusText = computed(() => {
  if (!maintenance.value) return '未加载'
  if (maintenance.value.lock_active) return '执行中'
  return maintenance.value.enabled ? '已开启' : '未开启'
})

const maintenanceTime = computed(() => {
  if (!maintenance.value) return '-'
  return `${pad2(maintenance.value.hour)}:${pad2(maintenance.value.minute)}`
})

const lastMaintenanceStatus = computed(() => {
  const status = maintenance.value?.last_run?.status
  if (!status) return '暂无'
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'skipped') return '跳过'
  return String(status)
})

const lastMaintenanceDetail = computed(() => {
  const lastRun = maintenance.value?.last_run
  if (!lastRun) return '尚未产生维护记录'
  if (lastRun.error) return String(lastRun.error)
  const runDate = lastRun.run_date ? `运行日期 ${lastRun.run_date}` : ''
  const report = isRecord(lastRun.report) ? `报告 ${lastRun.report.id ?? '-'}` : ''
  return [runDate, report].filter(Boolean).join(' / ') || '已记录'
})

const latestMaintenanceCards = computed(() => maintenanceCards(maintenance.value?.last_run))

const lastRefreshText = computed(() => {
  if (!lastRefreshedAt.value) return '尚未刷新'
  return `上次刷新 ${lastRefreshedAt.value.toLocaleTimeString('zh-CN', { hour12: false })}`
})

async function refresh() {
  loading.value = true
  try {
    await refreshAllData()
  } finally {
    loading.value = false
  }
}

async function refreshSilently() {
  try {
    await refreshAllData()
  } catch {
    // Keep the page calm during background polling; manual refresh still surfaces errors through visible state.
  }
}

async function refreshAllData() {
  const [healthResult, liveResult, readyResult, maintenanceResult, qualityResult, logsResult, tasksResult] = await Promise.allSettled([
      fetchHealth(),
      fetchLiveHealth(),
      fetchReadyHealth(),
      fetchMaintenanceStatus(),
      fetchDataQualityStatus(),
      fetchDataQualityLogs(),
      fetchWorkflowTasks(),
  ])
  health.value = toProbeState(healthResult, '基础健康检查')
  live.value = toProbeState(liveResult, 'API 进程存活')
  ready.value = toProbeState(readyResult, '数据库与 worker 就绪')
  if (maintenanceResult.status === 'fulfilled') maintenance.value = maintenanceResult.value
  if (qualityResult.status === 'fulfilled') qualityStatus.value = qualityResult.value
  if (logsResult.status === 'fulfilled') qualityLogs.value = logsResult.value
  if (tasksResult.status === 'fulfilled') tasks.value = tasksResult.value
  lastRefreshedAt.value = new Date()
}

async function refreshTasks() {
  tasks.value = await fetchWorkflowTasks()
  lastRefreshedAt.value = new Date()
}

async function triggerMaintenance() {
  maintenanceRunning.value = true
  try {
    const response = await runMaintenanceNow()
    ElMessage.success(`每日维护任务已创建，task_id=${response.task_id}`)
    await Promise.all([refreshTasks(), refreshMaintenance()])
  } finally {
    maintenanceRunning.value = false
  }
}

async function refreshMaintenance() {
  maintenance.value = await fetchMaintenanceStatus()
  lastRefreshedAt.value = new Date()
}

function startAutoRefresh() {
  stopAutoRefresh()
  autoRefreshTimer = window.setInterval(refreshSilently, autoRefreshSeconds * 1000)
}

function stopAutoRefresh() {
  if (autoRefreshTimer !== undefined) {
    window.clearInterval(autoRefreshTimer)
    autoRefreshTimer = undefined
  }
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
    partial_success: '部分完成',
    failed: '失败',
    cancelled: '已取消',
    skipped: '已跳过',
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

function severityText(severity: string) {
  const map: Record<string, string> = {
    error: '错误',
    warning: '警告',
    info: '信息',
    success: '正常',
  }
  return map[severity] || severity
}

function taskTypeText(type: string) {
  const map: Record<string, string> = {
    full_rebalance: '全流程',
    historical_market_init: '历史初始化',
    market_repair: '行情补齐',
    daily_maintenance: '每日维护',
  }
  return map[type] || type
}

function scopeText(scope?: string) {
  const map: Record<string, string> = {
    enabled: '启用池',
    core: '核心池',
    positions: '当前持仓',
    target: '目标组合',
    plans: '定投计划',
    all: '全市场',
    custom: '自定义',
  }
  return scope ? map[scope] || scope : '-'
}

function currentStepName(task: WorkflowTask) {
  if (!task.current_step) return '-'
  return task.steps.find((step) => step.step_key === task.current_step)?.step_name || task.current_step
}

function taskProgress(task: WorkflowTask) {
  if (!task.steps.length) return task.status === 'success' ? 100 : 0
  const done = task.steps.filter((step) => ['success', 'skipped'].includes(step.status)).length
  if (task.status === 'success' || task.status === 'partial_success') return 100
  return Math.round((done / task.steps.length) * 100)
}

function progressStatus(status: string) {
  if (status === 'success' || status === 'partial_success') return 'success'
  if (status === 'failed' || status === 'cancelled') return 'exception'
  return undefined
}

function taskDuration(task: WorkflowTask) {
  return durationText(task.started_at || task.created_at, task.finished_at)
}

function stepDuration(step: WorkflowTask['steps'][number]) {
  return durationText(step.started_at, step.finished_at)
}

function durationText(start?: string | null, end?: string | null) {
  if (!start) return '-'
  const startMs = new Date(start).getTime()
  const endMs = end ? new Date(end).getTime() : Date.now()
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) return '-'
  const seconds = Math.max(0, Math.round((endMs - startMs) / 1000))
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  if (minutes < 60) return `${minutes} 分 ${rest} 秒`
  const hours = Math.floor(minutes / 60)
  return `${hours} 小时 ${minutes % 60} 分`
}

function taskTargetSummary(task: WorkflowTask) {
  const payload = task.request_payload || {}
  const result = task.result_payload || {}
  const symbols = Array.isArray(payload.symbols) ? payload.symbols : Array.isArray(result.symbols) ? result.symbols : []
  if (symbols.length) return `${symbols.slice(0, 4).join('、')}${symbols.length > 4 ? ` 等 ${symbols.length} 只` : ''}`
  if (typeof payload.scope === 'string') return scopeText(payload.scope)
  if (typeof payload.sync_scope === 'string') return scopeText(payload.sync_scope)
  return '-'
}

function taskHint(task: WorkflowTask) {
  if (task.error_message) return userFriendlyMessage(task.error_message)
  if (task.status === 'pending') return '任务已创建，等待 worker 执行。'
  if (task.status === 'running') return `正在执行：${currentStepName(task)}`
  if (task.status === 'success') return '任务已完成。'
  if (task.status === 'partial_success') return '任务部分完成，请展开查看跳过步骤。'
  if (task.status === 'cancelled') return '任务已取消。'
  return '-'
}

function userFriendlyMessage(message?: string | null) {
  if (!message) return ''
  if (message.includes('tushare returned no fund_daily rows')) return 'Tushare 未返回该 ETF 在目标区间的日线行情。'
  if (message.includes('missing_trading_calendar')) return '交易日历缺失，请先同步交易日历。'
  if (message.includes('insufficient_history')) return '历史样本不足，请补齐更长周期行情或缩短分析周期。'
  if (message.includes('stale_market_data')) return '最新行情不够新，请补齐最近交易日行情。'
  if (message.includes('RemoteDisconnected') || message.includes('Connection aborted')) {
    return '外部数据源连接中断，建议稍后重试并适当提高请求间隔。'
  }
  return message
}

function summarizeStepPayload(payload?: Record<string, unknown> | null) {
  if (!payload) return '-'
  const cards = maintenanceCards(payload)
  if (cards.length) return cards.map((card) => `${card.title}：${card.value}`).join('；')
  const keys = ['status', 'success_count', 'failed_count', 'total_clean_rows', 'total_factor_rows', 'total_logs', 'run_id', 'order_count']
  const parts = keys.filter((key) => payload[key] != null).map((key) => `${fieldText(key)}=${payload[key]}`)
  return parts.join('；') || '执行完成'
}

function taskResultCards(task: WorkflowTask): ResultCard[] {
  if (task.task_type === 'daily_maintenance') {
    const payload = task.result_payload?.steps
    if (isRecord(payload)) {
      const maintenancePayload = payload.maintenance
      if (isRecord(maintenancePayload)) return maintenanceCards(maintenancePayload)
    }
  }
  return maintenanceCards(task.result_payload)
}

function maintenanceCards(payload?: Record<string, unknown> | null): ResultCard[] {
  if (!payload) return []
  const cards: ResultCard[] = []
  const market = recordValue(payload.market)
  const factors = recordValue(payload.factors)
  const strategy = recordValue(payload.strategy)
  const risk = recordValue(payload.risk)
  const rebalance = recordValue(payload.rebalance)
  const report = recordValue(payload.report)

  if (market) {
    const requested = numberText(market.requested_symbols)
    const success = numberText(market.success_count)
    const fresh = numberText(market.up_to_date_symbols)
    const cleanRows = numberText(market.total_clean_rows)
    cards.push({
      title: '行情同步',
      value: `${success}/${requested} 只`,
      detail: `已是最新 ${fresh} 只，新增清洗行情 ${cleanRows} 行。`,
    })
  }
  if (factors) {
    cards.push({
      title: '因子计算',
      value: `${numberText(factors.success_count)} 只`,
      detail: `本地因子总行数 ${numberText(factors.total_factor_rows)}，失败 ${numberText(factors.failed_count)} 只。`,
    })
  }
  if (strategy) {
    cards.push({
      title: '策略运行',
      value: `Run ${textValue(strategy.run_id)}`,
      detail: `${textValue(strategy.strategy_code)} 生成信号 ${numberText(strategy.signal_count)} 条，目标持仓 ${numberText(strategy.target_count)} 只。`,
    })
  }
  if (risk) {
    cards.push({
      title: '风控检查',
      value: `${numberText(risk.result_count)} 条`,
      detail: `需要调整 ${numberText(risk.adjusted_count)} 条，状态 ${statusText(textValue(risk.status))}。`,
    })
  }
  if (rebalance) {
    cards.push({
      title: '调仓建议',
      value: `${numberText(rebalance.order_count)} 条`,
      detail: `建议单日期 ${textValue(rebalance.order_date)}，仅供人工确认。`,
    })
  }
  if (report) {
    cards.push({
      title: '报告生成',
      value: `ID ${textValue(report.id)}`,
      detail: `${textValue(report.title)}。`,
    })
  }
  return cards
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function textValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

function numberText(value: unknown) {
  if (value === null || value === undefined || value === '') return '0'
  const parsed = Number(value)
  return Number.isFinite(parsed) ? String(parsed) : String(value)
}

function statusText(status: string) {
  return taskStatusText(status)
}

function fieldText(key: string) {
  const map: Record<string, string> = {
    status: '状态',
    success_count: '成功数',
    failed_count: '失败数',
    total_clean_rows: '清洗行情行数',
    total_factor_rows: '因子行数',
    total_logs: '日志数',
    run_id: '运行ID',
    order_count: '建议单数',
  }
  return map[key] || key
}

function pad2(value: number) {
  return String(value).padStart(2, '0')
}
</script>
