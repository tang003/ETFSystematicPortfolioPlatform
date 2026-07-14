<template>
  <div class="page-grid">
    <section class="panel span-4">
      <div class="panel-header">
        <h2>流程参数</h2>
        <el-tag :type="running ? 'warning' : taskStatusType">{{ taskStatusText }}</el-tag>
      </div>
      <el-form label-width="92px">
        <el-form-item label="分析周期">
          <el-segmented v-model="datePreset" :options="datePresetOptions" />
        </el-form-item>
        <el-form-item v-if="datePreset === 'custom'" label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item label="研究范围">
          <el-select v-model="syncScope">
            <el-option label="核心池：持仓 + 目标组合 + 定投 + 启用 ETF" value="core" />
            <el-option label="当前持仓" value="positions" />
            <el-option label="目标组合" value="target" />
            <el-option label="定投计划" value="plans" />
            <el-option label="启用 ETF" value="enabled" />
            <el-option label="全市场基础池" value="all" />
            <el-option label="自定义代码" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="syncScope === 'custom'" label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="多个代码用逗号或空格分隔，例如 510300, 513500" />
        </el-form-item>
        <el-form-item label="同步数量">
          <el-input-number v-model="maxSymbols" :min="1" :max="50" />
          <span class="form-note">控制本次最多处理多少只 ETF，避免一次任务过大。</span>
        </el-form-item>
        <el-form-item label="日历源">
          <el-select v-model="calendarSource">
            <el-option label="Tushare trade_cal" value="tushare" />
          </el-select>
        </el-form-item>
        <el-form-item label="行情源">
          <el-select v-model="marketSource">
            <el-option label="Tushare fund_daily" value="tushare" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求间隔">
          <el-input-number v-model="requestIntervalSeconds" :min="0" :max="10" :step="0.5" />
        </el-form-item>
        <el-form-item label="增量同步">
          <el-switch v-model="incrementalSync" />
        </el-form-item>
        <el-form-item label="严格门禁">
          <el-switch v-model="strictDataValidation" />
        </el-form-item>
        <el-form-item label="最少样本">
          <el-input-number v-model="minimumHistoryBars" :min="20" :max="1000" :step="20" />
        </el-form-item>
        <el-form-item label="策略代码">
          <el-input v-model="strategyCode" />
        </el-form-item>
        <el-form-item label="组合市值">
          <el-input-number v-model="portfolioValue" :min="1000" :step="10000" />
        </el-form-item>
        <el-form-item label="生成报告">
          <el-switch v-model="shouldGenerateReport" />
        </el-form-item>
        <el-form-item label="流程提示" class="workflow-hint-item">
          <div class="source-hint">
            <strong>{{ workflowHintTitle }}</strong>
            <p>{{ workflowHintText }}</p>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="running" @click="startWorkflow">创建后台任务</el-button>
          <el-button :disabled="running" @click="resetTask">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <h2>任务进度</h2>
        <div class="task-tags">
          <el-tag v-if="task" type="info">task_id: {{ task.id }}</el-tag>
          <el-tag v-if="runId" type="success">run_id: {{ runId }}</el-tag>
          <el-button size="small" :disabled="!task" @click="refreshTask">刷新</el-button>
          <el-button size="small" type="warning" :disabled="!canCancel" @click="cancelTask">取消</el-button>
          <el-button size="small" type="primary" :disabled="!canRetry" @click="retryFailed">重试失败步骤</el-button>
        </div>
      </div>
      <el-steps :active="activeStep" finish-status="success" process-status="process" direction="vertical">
        <el-step v-for="step in displaySteps" :key="step.key" :title="step.title" :description="step.description" :status="step.status" />
      </el-steps>
    </section>

    <section class="panel span-5">
      <div class="panel-header">
        <h2>最近任务</h2>
        <el-button text @click="loadTasks">刷新</el-button>
      </div>
      <el-table :data="tasks" height="360" highlight-current-row @current-change="selectTask">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">{{ statusText(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170" />
      </el-table>
    </section>

    <section class="panel span-7">
      <div class="panel-header">
        <h2>任务日志</h2>
        <el-tag v-if="task?.error_message" type="danger">{{ task.error_message }}</el-tag>
      </div>
      <el-table :data="logs" height="360">
        <el-table-column prop="time" label="时间" width="170" />
        <el-table-column prop="step" label="步骤" width="170" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="message" label="说明" min-width="300" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { cancelWorkflowTask, fetchWorkflowTask, fetchWorkflowTasks, retryFailedWorkflowTask, startWorkflowTask, type WorkflowTask, type WorkflowTaskStep } from '../api/client'

type StepStatus = 'wait' | 'process' | 'finish' | 'error' | 'success'

interface DisplayStep {
  key: string
  title: string
  description: string
  status: StepStatus
}

const stepDescriptions: Record<string, string> = {
  calendar: '写入 A 股交易日历，用于缺失数据检查。',
  market: '拉取并清洗行情，同时检查最近交易日和历史样本数量。',
  quality: '检查日期范围内的缺失交易日。',
  factors: '生成趋势、动量、波动、回撤、流动性等评分。',
  strategy: '生成 Alpha 信号和目标组合。',
  risk: '检查组合约束并写入风控结果。',
  rebalance: '按目标权重和组合市值生成建议订单。',
  report: '汇总策略、组合、风控、调仓和回测信息。',
}

const today = new Date().toISOString().slice(0, 10)
const lastYear = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const datePreset = ref<'6m' | '1y' | '3y' | '5y' | 'inception' | 'custom'>('1y')
const dateRange = ref<[string, string]>([lastYear, today])
const syncScope = ref<'core' | 'positions' | 'target' | 'plans' | 'enabled' | 'all' | 'custom'>('core')
const symbolsText = ref('')
const maxSymbols = ref(20)
const calendarSource = ref('tushare')
const marketSource = ref('tushare')
const requestIntervalSeconds = ref(1.5)
const incrementalSync = ref(true)
const strictDataValidation = ref(true)
const minimumHistoryBars = ref(200)
const strategyCode = ref('core_etf_rotation')
const portfolioValue = ref(100000)
const shouldGenerateReport = ref(true)
const task = ref<WorkflowTask>()
const tasks = ref<WorkflowTask[]>([])
const running = ref(false)
let timer: number | undefined

const datePresetOptions = [
  { label: '半年', value: '6m' },
  { label: '1 年', value: '1y' },
  { label: '3 年', value: '3y' },
  { label: '5 年', value: '5y' },
  { label: '成立以来', value: 'inception' },
  { label: '自定义', value: 'custom' },
]

onMounted(loadTasks)

const displaySteps = computed<DisplayStep[]>(() => {
  if (!task.value?.steps.length) return defaultSteps()
  return task.value.steps.map((step) => ({
    key: step.step_key,
    title: step.step_name,
    description: step.message || stepDescriptions[step.step_key] || '',
    status: mapStepStatus(step.status),
  }))
})

const activeStep = computed(() => {
  const index = displaySteps.value.findIndex((step) => step.status === 'process')
  if (index >= 0) return index
  const failed = displaySteps.value.findIndex((step) => step.status === 'error')
  if (failed >= 0) return failed
  return displaySteps.value.filter((step) => step.status === 'finish' || step.status === 'success').length
})

const taskStatusText = computed(() => {
  if (running.value) return '执行中'
  if (!task.value) return '待执行'
  return statusText(task.value.status)
})

const taskStatusType = computed(() => {
  if (!task.value) return 'info'
  if (task.value.status === 'success' || task.value.status === 'partial_success') return 'success'
  if (task.value.status === 'failed' || task.value.status === 'cancelled') return 'danger'
  return 'warning'
})

const runId = computed(() => Number(task.value?.result_payload?.run_id || 0) || undefined)
const canCancel = computed(() => task.value && ['pending', 'running'].includes(task.value.status))
const canRetry = computed(() => task.value?.status === 'failed' && task.value.steps.some((step) => step.status === 'failed'))
const workflowHintTitle = computed(() => {
  return 'Tushare-only 真实数据模式'
})

const workflowHintText = computed(() => {
  const scopeText = syncScope.value === 'custom' ? `自定义代码 ${splitSymbols()?.join('、') || '未填写'}` : scopeLabel(syncScope.value)
  const dateText = datePreset.value === 'custom' ? `${dateRange.value[0]} 至 ${dateRange.value[1]}` : datePresetLabel(datePreset.value)
  return incrementalSync.value
    ? `系统只使用 Tushare。本次将按“${scopeText}”自动选择 ETF，分析周期为“${dateText}”，最多处理 ${maxSymbols.value} 只；已开启增量同步和数据门禁。`
    : `系统只使用 Tushare。本次将按“${scopeText}”自动选择 ETF，分析周期为“${dateText}”，最多处理 ${maxSymbols.value} 只；全量模式建议缩短周期。`
})

const logs = computed(() => {
  if (!task.value) return []
  return task.value.steps
    .filter((step) => step.status !== 'pending' || step.message)
    .map((step) => ({
      time: step.finished_at || step.started_at || task.value?.created_at || '',
      step: step.step_name,
      status: statusText(step.status),
      message: step.message || summarizePayload(step),
    }))
    .reverse()
})

async function startWorkflow() {
  running.value = true
  try {
    const response = await startWorkflowTask({
      symbols: splitSymbols(),
      sync_scope: syncScope.value,
      date_preset: datePreset.value,
      start_date: datePreset.value === 'custom' ? dateRange.value[0] : undefined,
      end_date: datePreset.value === 'custom' ? dateRange.value[1] : undefined,
      max_symbols: maxSymbols.value,
      calendar_source: calendarSource.value,
      market_source: marketSource.value,
      incremental_sync: incrementalSync.value,
      request_interval_seconds: requestIntervalSeconds.value,
      strict_data_validation: strictDataValidation.value,
      minimum_history_bars: minimumHistoryBars.value,
      strategy_code: strategyCode.value,
      portfolio_value: portfolioValue.value,
      generate_report: shouldGenerateReport.value,
    })
    task.value = await fetchWorkflowTask(response.task_id)
    await loadTasks()
    ElMessage.success(`后台任务已创建，task_id=${response.task_id}`)
    startPolling(response.task_id)
  } catch (error) {
    running.value = false
    ElMessage.error(error instanceof Error ? error.message : '任务创建失败')
  }
}

async function refreshTask() {
  if (!task.value) return
  task.value = await fetchWorkflowTask(task.value.id)
}

async function loadTasks() {
  tasks.value = await fetchWorkflowTasks()
}

async function selectTask(row: WorkflowTask | undefined) {
  if (!row) return
  stopPolling()
  task.value = await fetchWorkflowTask(row.id)
  running.value = ['pending', 'running'].includes(task.value.status)
  if (running.value) startPolling(task.value.id)
}

async function cancelTask() {
  if (!task.value) return
  task.value = await cancelWorkflowTask(task.value.id)
  running.value = false
  stopPolling()
  await loadTasks()
  ElMessage.warning('任务已取消')
}

async function retryFailed() {
  if (!task.value) return
  const response = await retryFailedWorkflowTask(task.value.id)
  task.value = await fetchWorkflowTask(response.task_id)
  running.value = true
  await loadTasks()
  ElMessage.success('已重新执行失败步骤')
  startPolling(response.task_id)
}

function startPolling(taskId: number) {
  stopPolling()
  timer = window.setInterval(async () => {
    try {
      task.value = await fetchWorkflowTask(taskId)
      if (['success', 'partial_success', 'failed', 'cancelled'].includes(task.value.status)) {
        running.value = false
        stopPolling()
        await loadTasks()
        if (task.value.status === 'success') ElMessage.success('后台流程执行完成')
        if (task.value.status === 'partial_success') ElMessage.warning('后台流程部分完成')
        if (task.value.status === 'failed') ElMessage.error(task.value.error_message || '后台流程执行失败')
        if (task.value.status === 'cancelled') ElMessage.warning('后台流程已取消')
      }
    } catch (error) {
      running.value = false
      stopPolling()
      ElMessage.error(error instanceof Error ? error.message : '任务轮询失败')
    }
  }, 2000)
}

function resetTask() {
  stopPolling()
  running.value = false
  task.value = undefined
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = undefined
  }
}

function defaultSteps(): DisplayStep[] {
  return [
    { key: 'calendar', title: '同步交易日历', description: stepDescriptions.calendar, status: 'wait' },
    { key: 'market', title: '同步 ETF 行情', description: stepDescriptions.market, status: 'wait' },
    { key: 'quality', title: '检查数据质量', description: stepDescriptions.quality, status: 'wait' },
    { key: 'factors', title: '计算因子', description: stepDescriptions.factors, status: 'wait' },
    { key: 'strategy', title: '运行策略', description: stepDescriptions.strategy, status: 'wait' },
    { key: 'risk', title: '执行风控', description: stepDescriptions.risk, status: 'wait' },
    { key: 'rebalance', title: '生成调仓单', description: stepDescriptions.rebalance, status: 'wait' },
    { key: 'report', title: '生成月度报告', description: stepDescriptions.report, status: 'wait' },
  ]
}

function mapStepStatus(status: string): StepStatus {
  if (status === 'running') return 'process'
  if (status === 'success') return 'finish'
  if (status === 'failed' || status === 'cancelled') return 'error'
  if (status === 'skipped') return 'success'
  return 'wait'
}

function statusText(status: string) {
  const statusMap: Record<string, string> = {
    pending: '等待',
    running: '执行中',
    success: '完成',
    partial_success: '部分完成',
    failed: '失败',
    cancelled: '已取消',
    skipped: '跳过',
  }
  return statusMap[status] || status
}

function summarizePayload(step: WorkflowTaskStep) {
  if (!step.result_payload) return ''
  return Object.entries(step.result_payload)
    .filter(([key]) => ['status', 'success_count', 'failed_count', 'total_clean_rows', 'total_factor_rows', 'run_id', 'target_count', 'result_count', 'order_count', 'id'].includes(key))
    .map(([key, value]) => `${key}=${String(value)}`)
    .join('，')
}

function splitSymbols() {
  if (syncScope.value !== 'custom') return undefined
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
}

function scopeLabel(value: string) {
  const map: Record<string, string> = {
    core: '核心池',
    positions: '当前持仓',
    target: '目标组合',
    plans: '定投计划',
    enabled: '启用 ETF',
    all: '全市场基础池',
    custom: '自定义代码',
  }
  return map[value] || value
}

function datePresetLabel(value: string) {
  const map: Record<string, string> = {
    '6m': '最近半年',
    '1y': '最近 1 年',
    '3y': '最近 3 年',
    '5y': '最近 5 年',
    inception: '成立以来',
    custom: '自定义日期',
  }
  return map[value] || value
}

onBeforeUnmount(stopPolling)
</script>
