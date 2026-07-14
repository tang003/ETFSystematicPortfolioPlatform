<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>运行回测</h2>
        <el-button type="primary" :loading="actionLoading" @click="runBacktestFlow">开始回测</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="回测模式">
          <el-select v-model="form.strategy_code">
            <el-option label="策略月度调仓" value="core_etf_rotation_monthly" />
            <el-option label="等权买入持有" value="equal_weight_buy_and_hold" />
          </el-select>
        </el-form-item>
        <el-form-item label="回测名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分析周期">
          <el-segmented v-model="datePreset" :options="analysisPresetOptions" @change="applyPreset" />
          <span class="form-note">{{ rangeLabel }}</span>
        </el-form-item>
        <el-form-item v-if="datePreset === 'custom'" label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" :clearable="false" />
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="多个代码用逗号分隔，留空使用默认样本" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="form.initial_cash" :min="1000" :step="10000" />
        </el-form-item>
        <el-form-item label="每月追加">
          <el-input-number v-model="form.monthly_contribution" :min="0" :step="1000" />
        </el-form-item>
        <el-form-item label="手续费率">
          <el-input-number v-model="form.fee_rate" :min="0" :step="0.0005" :precision="4" />
        </el-form-item>
        <el-form-item label="滑点率">
          <el-input-number v-model="form.slippage_rate" :min="0" :step="0.0005" :precision="4" />
        </el-form-item>
      </el-form>
    </section>
    <section class="panel span-4">
      <h2>回测记录</h2>
      <el-table :data="runs" height="360" highlight-current-row @current-change="selectRun">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="status" label="状态" width="100" />
      </el-table>
    </section>
    <section class="panel span-8">
      <h2>净值曲线</h2>
      <div ref="chartRef" class="chart"></div>
    </section>
    <section class="panel span-12">
      <h2>回测指标</h2>
      <el-table :data="metrics" height="260">
        <el-table-column prop="metric_name" label="指标" min-width="180" />
        <el-table-column prop="metric_value" label="数值" min-width="160" />
        <el-table-column prop="metric_unit" label="单位" width="120" />
      </el-table>
    </section>
    <section class="panel span-12">
      <h2>交易记录</h2>
      <el-table :data="trades" height="320">
        <el-table-column prop="trade_date" label="日期" width="120" />
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="action" label="方向" width="90" />
        <el-table-column prop="price" label="价格" width="110" />
        <el-table-column prop="quantity" label="数量" width="140" />
        <el-table-column prop="amount" label="金额" width="140" />
        <el-table-column prop="reason" label="原因" min-width="220" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchBacktestCurve, fetchBacktestMetrics, fetchBacktestRuns, fetchBacktestTrades, runBacktest, type BacktestCurvePoint, type BacktestMetric, type BacktestRun, type BacktestTrade } from '../api/client'
import { analysisPresetOptions, buildPresetRange, presetLabel, type AnalysisPreset } from '../datePresets'

const runs = ref<BacktestRun[]>([])
const curve = ref<BacktestCurvePoint[]>([])
const metrics = ref<BacktestMetric[]>([])
const trades = ref<BacktestTrade[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const chartRef = ref<HTMLElement>()
const datePreset = ref<AnalysisPreset>('1y')
const dateRange = ref<[string, string]>(buildPresetRange(datePreset.value))
const symbolsText = ref('510300,159915')
const rangeLabel = computed(() => `${presetLabel(datePreset.value)}：${dateRange.value[0]} 至 ${dateRange.value[1]}`)
const form = ref({
  strategy_code: 'core_etf_rotation_monthly',
  name: '策略月度调仓回测',
  initial_cash: 100000,
  monthly_contribution: 3000,
  fee_rate: 0.001,
  slippage_rate: 0.001,
})

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    runs.value = await fetchBacktestRuns()
    if (runs.value[0]) await loadRun(runs.value[0].id)
  } finally {
    loading.value = false
  }
}

async function selectRun(row: BacktestRun | undefined) {
  if (row) await loadRun(row.id)
}

async function loadRun(id: number) {
  ;[curve.value, metrics.value, trades.value] = await Promise.all([fetchBacktestCurve(id), fetchBacktestMetrics(id), fetchBacktestTrades(id)])
  await nextTick()
  if (chartRef.value) {
    echarts.init(chartRef.value).setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: curve.value.map((item) => item.trade_date) },
      yAxis: { type: 'value', scale: true },
      series: [{ type: 'line', data: curve.value.map((item) => Number(item.total_equity ?? 0)), smooth: true, symbolSize: 4, itemStyle: { color: '#0f766e' } }],
    })
  }
}

async function runBacktestFlow() {
  actionLoading.value = true
  try {
    const result = await runBacktest({
      strategy_code: form.value.strategy_code,
      name: form.value.name,
      symbols: splitSymbols(),
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      initial_cash: form.value.initial_cash,
      monthly_contribution: form.value.monthly_contribution,
      fee_rate: form.value.fee_rate,
      slippage_rate: form.value.slippage_rate,
    })
    ElMessage.success(`回测完成，backtest_id=${String(result.backtest_id ?? '-')}`)
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '回测失败')
  } finally {
    actionLoading.value = false
  }
}

function splitSymbols() {
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
}

function applyPreset() {
  if (datePreset.value !== 'custom') {
    dateRange.value = buildPresetRange(datePreset.value)
  }
}
</script>
