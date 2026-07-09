<template>
  <div class="page-grid">
    <section class="panel span-4">
      <div class="panel-header">
        <h2>流程参数</h2>
        <el-tag :type="running ? 'warning' : 'info'">{{ running ? '执行中' : '待执行' }}</el-tag>
      </div>
      <el-form label-width="92px">
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="多个代码用逗号分隔；留空表示全部启用 ETF" />
        </el-form-item>
        <el-form-item label="同步数量">
          <el-input-number v-model="maxSymbols" :min="1" :max="50" />
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
        <el-form-item>
          <el-button type="primary" :loading="running" @click="runWorkflow">运行完整流程</el-button>
          <el-button :disabled="running" @click="resetSteps">重置状态</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <h2>执行步骤</h2>
        <el-tag v-if="latestRunId" type="success">run_id: {{ latestRunId }}</el-tag>
      </div>
      <el-steps :active="activeStep" finish-status="success" process-status="process" direction="vertical">
        <el-step v-for="step in steps" :key="step.key" :title="step.title" :description="step.description" :status="step.status" />
      </el-steps>
    </section>

    <section class="panel span-12">
      <div class="panel-header">
        <h2>执行日志</h2>
        <el-button text @click="logs = []">清空</el-button>
      </div>
      <el-table :data="logs" height="320">
        <el-table-column prop="time" label="时间" width="160" />
        <el-table-column prop="step" label="步骤" width="160" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="message" label="说明" min-width="360" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { calculateFactors, checkDataQuality, checkRisk, generateMonthlyReport, generateRebalanceOrders, runStrategy, syncCalendar, syncMarket } from '../api/client'

type StepStatus = 'wait' | 'process' | 'finish' | 'error' | 'success'

interface WorkflowStep {
  key: string
  title: string
  description: string
  status: StepStatus
}

interface WorkflowLog {
  time: string
  step: string
  status: string
  message: string
}

const today = new Date().toISOString().slice(0, 10)
const lastYear = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([lastYear, today])
const symbolsText = ref('510300,159915')
const maxSymbols = ref(10)
const strategyCode = ref('core_etf_rotation')
const portfolioValue = ref(100000)
const shouldGenerateReport = ref(true)
const running = ref(false)
const latestRunId = ref<number>()
const logs = ref<WorkflowLog[]>([])
const steps = ref<WorkflowStep[]>(createSteps())

const activeStep = computed(() => {
  const index = steps.value.findIndex((step) => step.status === 'process')
  if (index >= 0) return index
  const failed = steps.value.findIndex((step) => step.status === 'error')
  if (failed >= 0) return failed
  return steps.value.filter((step) => step.status === 'finish' || step.status === 'success').length
})

async function runWorkflow() {
  running.value = true
  resetSteps()
  try {
    const symbols = splitSymbols()
    await executeStep('calendar', () => syncCalendar({ start_date: dateRange.value[0], end_date: dateRange.value[1], market: 'CN' }))
    await executeStep('market', () => syncMarket({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols, max_symbols: maxSymbols.value, clean_after_sync: true }))
    if (symbols.length) {
      await executeStep('quality', () => checkDataQuality({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols }))
    } else {
      skipStep('quality', '未填写 ETF 代码，跳过缺失数据检查。')
    }
    await executeStep('factors', () => calculateFactors({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols }))
    const strategyResult = await executeStep('strategy', () => runStrategy({ strategy_code: strategyCode.value, run_date: dateRange.value[1], run_type: 'manual' }))
    const runId = Number(strategyResult.run_id)
    if (!Number.isFinite(runId)) throw new Error('策略运行结果缺少有效 run_id')
    latestRunId.value = runId
    await executeStep('risk', () => checkRisk({ run_id: runId }))
    await executeStep('rebalance', () => generateRebalanceOrders({ run_id: runId, portfolio_value: portfolioValue.value }))
    if (shouldGenerateReport.value) {
      await executeStep('report', () => generateMonthlyReport({ run_id: runId, report_date: dateRange.value[1] }))
    } else {
      skipStep('report', '已关闭报告生成。')
    }
    ElMessage.success('完整流程执行完成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '流程执行失败')
  } finally {
    running.value = false
  }
}

async function executeStep(key: string, action: () => Promise<Record<string, unknown> | Record<string, unknown>[]>) {
  setStepStatus(key, 'process')
  addLog(key, '执行中', '开始执行')
  try {
    const result = await action()
    setStepStatus(key, 'finish')
    addLog(key, '完成', summarizeResult(result))
    return Array.isArray(result) ? {} : result
  } catch (error) {
    setStepStatus(key, 'error')
    addLog(key, '失败', error instanceof Error ? error.message : '执行失败')
    throw error
  }
}

function skipStep(key: string, message: string) {
  setStepStatus(key, 'success')
  addLog(key, '跳过', message)
}

function resetSteps() {
  latestRunId.value = undefined
  steps.value = createSteps()
}

function createSteps(): WorkflowStep[] {
  return [
    { key: 'calendar', title: '同步交易日历', description: '写入 A 股交易日历，用于缺失数据检查。', status: 'wait' },
    { key: 'market', title: '同步 ETF 行情', description: '拉取原始行情并清洗到 clean 表。', status: 'wait' },
    { key: 'quality', title: '检查数据质量', description: '检查日期范围内的缺失交易日。', status: 'wait' },
    { key: 'factors', title: '计算因子', description: '生成趋势、动量、波动、回撤、流动性等评分。', status: 'wait' },
    { key: 'strategy', title: '运行策略', description: '生成 Alpha 信号和目标组合。', status: 'wait' },
    { key: 'risk', title: '执行风控', description: '检查组合约束并写入风控结果。', status: 'wait' },
    { key: 'rebalance', title: '生成调仓单', description: '按目标权重和组合市值生成建议订单。', status: 'wait' },
    { key: 'report', title: '生成月度报告', description: '汇总策略、组合、风控、调仓和回测信息。', status: 'wait' },
  ]
}

function setStepStatus(key: string, status: StepStatus) {
  const step = steps.value.find((item) => item.key === key)
  if (step) step.status = status
}

function addLog(step: string, status: string, message: string) {
  logs.value.unshift({ time: new Date().toLocaleTimeString(), step: stepTitle(step), status, message })
}

function stepTitle(key: string) {
  return steps.value.find((step) => step.key === key)?.title ?? key
}

function summarizeResult(result: Record<string, unknown> | Record<string, unknown>[]) {
  if (Array.isArray(result)) return `返回 ${result.length} 条结果`
  const entries = Object.entries(result)
    .filter(([key]) => ['status', 'success_count', 'failed_count', 'total_clean_rows', 'total_factor_rows', 'run_id', 'target_count', 'result_count', 'order_count', 'id'].includes(key))
    .map(([key, value]) => `${key}=${String(value)}`)
  return entries.length ? entries.join('，') : '执行成功'
}

function splitSymbols() {
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
}
</script>
