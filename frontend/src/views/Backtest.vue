<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>运行回测</h2>
        <el-button type="primary" :loading="actionLoading" @click="runBacktestFlow">开始回测</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="回测名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="多个代码用逗号分隔，留空使用默认样本" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="form.initial_cash" :min="1000" :step="10000" />
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
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchBacktestCurve, fetchBacktestMetrics, fetchBacktestRuns, runBacktest, type BacktestCurvePoint, type BacktestMetric, type BacktestRun } from '../api/client'

const runs = ref<BacktestRun[]>([])
const curve = ref<BacktestCurvePoint[]>([])
const metrics = ref<BacktestMetric[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const chartRef = ref<HTMLElement>()
const today = new Date().toISOString().slice(0, 10)
const start = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([start, today])
const symbolsText = ref('510300,159915')
const form = ref({ strategy_code: 'equal_weight_buy_and_hold', name: '等权买入持有回测', initial_cash: 100000 })

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
  ;[curve.value, metrics.value] = await Promise.all([fetchBacktestCurve(id), fetchBacktestMetrics(id)])
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
</script>
