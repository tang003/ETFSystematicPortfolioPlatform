<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-3">
      <div class="metric">当前持仓市值<strong>{{ formatMoney(totalMarketValue) }}</strong></div>
    </section>
    <section class="panel span-3">
      <div class="metric">目标 ETF 数<strong>{{ targetRows.length }}</strong></div>
    </section>
    <section class="panel span-3">
      <div class="metric">低配资产<strong>{{ underweightCount }}</strong></div>
    </section>
    <section class="panel span-3">
      <div class="metric">高配资产<strong>{{ overweightCount }}</strong></div>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <h2>组合偏离总览</h2>
        <el-button :loading="loading" @click="refresh">刷新</el-button>
      </div>
      <el-table :data="workbenchRows" height="430" :row-class-name="rowClassName">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="currentWeightText" label="当前权重" width="120" />
        <el-table-column prop="targetWeightText" label="目标权重" width="120" />
        <el-table-column prop="diffText" label="偏离" width="110" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ row.statusText }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="marketValueText" label="当前市值" width="130" />
        <el-table-column prop="suggestion" label="解释" min-width="260" />
      </el-table>
    </section>

    <section class="panel span-4">
      <h2>组合提示</h2>
      <div class="insight-list">
        <div class="insight-item">
          <span>偏离最大</span>
          <strong>{{ largestDeviation?.symbol || '-' }}</strong>
          <p>{{ largestDeviation?.suggestion || '暂无持仓或目标组合数据。' }}</p>
        </div>
        <div class="insight-item">
          <span>本期定投优先</span>
          <strong>{{ topInvestment?.symbol || '-' }}</strong>
          <p>{{ topInvestment ? `${topInvestment.symbol} 建议投入 ${formatMoney(Number(topInvestment.suggested_amount))}` : '暂无定投建议。' }}</p>
        </div>
        <div class="insight-item">
          <span>调仓动作</span>
          <strong>{{ activeOrderCount }}</strong>
          <p>{{ activeOrderCount ? '已有买入或卖出建议，执行前仍需要人工确认。' : '暂无明显调仓动作。' }}</p>
        </div>
      </div>
    </section>

    <section class="panel span-4">
      <h2>当前持仓</h2>
      <el-table :data="positions" height="320">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="market_value" label="市值" width="130" />
        <el-table-column prop="weight" label="权重" />
      </el-table>
    </section>

    <section class="panel span-4">
      <h2>定投建议</h2>
      <el-table :data="investmentSuggestions" height="320">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="suggested_amount" label="建议金额" width="130" />
        <el-table-column prop="reason" label="原因" min-width="200" />
      </el-table>
    </section>

    <section class="panel span-4">
      <h2>调仓建议</h2>
      <el-table :data="orders" height="320">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column label="方向" width="90">
          <template #default="{ row }">{{ actionText(row.action) }}</template>
        </el-table-column>
        <el-table-column prop="estimated_amount" label="估算金额" width="130" />
        <el-table-column prop="reason" label="说明" min-width="200" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchHoldingAnalysis,
  fetchInvestmentPlanSuggestions,
  fetchInvestmentPlans,
  fetchPositions,
  fetchRebalanceOrders,
  fetchTargetPortfolio,
  type HoldingAnalysis,
  type InvestmentPlan,
  type InvestmentPlanSuggestion,
  type PortfolioPosition,
  type RebalanceOrder,
  type TargetPortfolio,
} from '../api/client'

interface WorkbenchRow {
  symbol: string
  currentWeight: number
  targetWeight: number
  diff: number
  currentWeightText: string
  targetWeightText: string
  diffText: string
  marketValueText: string
  status: 'underweight' | 'overweight' | 'balanced' | 'exit'
  statusText: string
  suggestion: string
}

const loading = ref(false)
const positions = ref<PortfolioPosition[]>([])
const targets = ref<TargetPortfolio[]>([])
const holdingAnalysis = ref<HoldingAnalysis[]>([])
const plans = ref<InvestmentPlan[]>([])
const investmentSuggestions = ref<InvestmentPlanSuggestion[]>([])
const orders = ref<RebalanceOrder[]>([])

onMounted(refresh)

const totalMarketValue = computed(() => positions.value.reduce((sum, item) => sum + Number(item.market_value || 0), 0))
const targetRows = computed(() => targets.value.filter((item) => Number(item.final_target_weight || item.raw_target_weight || 0) > 0))
const activeOrderCount = computed(() => orders.value.filter((item) => item.action !== 'HOLD').length)

const workbenchRows = computed<WorkbenchRow[]>(() => {
  const positionMap = new Map(positions.value.map((item) => [item.symbol, item]))
  const targetMap = new Map(targets.value.map((item) => [item.symbol, item]))
  const analysisMap = new Map(holdingAnalysis.value.map((item) => [item.symbol, item]))
  const symbols = Array.from(new Set([...positionMap.keys(), ...targetMap.keys()])).sort()
  return symbols.map((symbol) => {
    const position = positionMap.get(symbol)
    const target = targetMap.get(symbol)
    const currentWeight = Number(position?.weight || 0)
    const targetWeight = Number(target?.final_target_weight || target?.raw_target_weight || 0)
    const diff = targetWeight - currentWeight
    const analysis = analysisMap.get(symbol)
    const status = resolveStatus(currentWeight, targetWeight, diff)
    return {
      symbol,
      currentWeight,
      targetWeight,
      diff,
      currentWeightText: formatPercent(currentWeight),
      targetWeightText: formatPercent(targetWeight),
      diffText: formatSignedPercent(diff),
      marketValueText: formatMoney(Number(position?.market_value || 0)),
      status,
      statusText: statusText(status),
      suggestion: analysis?.reason || buildSuggestion(symbol, status, diff),
    }
  }).sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))
})

const underweightCount = computed(() => workbenchRows.value.filter((item) => item.status === 'underweight').length)
const overweightCount = computed(() => workbenchRows.value.filter((item) => item.status === 'overweight' || item.status === 'exit').length)
const largestDeviation = computed(() => workbenchRows.value[0])
const topInvestment = computed(() => investmentSuggestions.value[0])

async function refresh() {
  loading.value = true
  try {
    const [positionData, targetData, analysisData, planData, orderData] = await Promise.all([
      fetchPositions(),
      fetchTargetPortfolio(),
      fetchHoldingAnalysis(),
      fetchInvestmentPlans(),
      fetchRebalanceOrders(),
    ])
    positions.value = positionData
    targets.value = targetData
    holdingAnalysis.value = analysisData
    plans.value = planData
    orders.value = orderData
    investmentSuggestions.value = planData.length ? await fetchInvestmentPlanSuggestions(planData[0].id) : []
  } finally {
    loading.value = false
  }
}

function resolveStatus(current: number, target: number, diff: number): WorkbenchRow['status'] {
  if (target === 0 && current > 0) return 'exit'
  if (diff >= 0.03) return 'underweight'
  if (diff <= -0.03) return 'overweight'
  return 'balanced'
}

function statusText(status: WorkbenchRow['status']) {
  const map = { underweight: '低配', overweight: '高配', balanced: '接近目标', exit: '考虑退出' }
  return map[status]
}

function statusTag(status: WorkbenchRow['status']) {
  if (status === 'underweight') return 'success'
  if (status === 'overweight' || status === 'exit') return 'warning'
  return 'info'
}

function actionText(action: string) {
  const map: Record<string, string> = { BUY: '买入', SELL: '卖出', HOLD: '持有' }
  return map[action] || action
}

function buildSuggestion(symbol: string, status: WorkbenchRow['status'], diff: number) {
  if (status === 'underweight') return `${symbol} 当前低于目标权重 ${formatPercent(Math.abs(diff))}，可作为定投或加仓优先项。`
  if (status === 'overweight') return `${symbol} 当前高于目标权重 ${formatPercent(Math.abs(diff))}，新增资金可暂缓配置。`
  if (status === 'exit') return `${symbol} 当前有持仓但目标权重为 0，建议复核是否逐步退出。`
  return `${symbol} 当前权重接近目标，可继续持有。`
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`
}

function formatSignedPercent(value: number) {
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatPercent(value)}`
}

function formatMoney(value: number) {
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function rowClassName({ row }: { row: WorkbenchRow }) {
  return `workbench-row-${row.status}`
}
</script>
