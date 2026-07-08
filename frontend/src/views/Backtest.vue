<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-4">
      <h2>Backtest Runs</h2>
      <el-table :data="runs" height="360" highlight-current-row @current-change="selectRun">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="Name" min-width="180" />
        <el-table-column prop="status" label="Status" width="100" />
      </el-table>
    </section>
    <section class="panel span-8">
      <h2>Equity Curve</h2>
      <div ref="chartRef" class="chart"></div>
    </section>
    <section class="panel span-12">
      <h2>Metrics</h2>
      <el-table :data="metrics" height="260">
        <el-table-column prop="metric_name" label="Metric" min-width="180" />
        <el-table-column prop="metric_value" label="Value" min-width="160" />
        <el-table-column prop="metric_unit" label="Unit" width="120" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchBacktestCurve, fetchBacktestMetrics, fetchBacktestRuns, type BacktestCurvePoint, type BacktestMetric, type BacktestRun } from '../api/client'

const runs = ref<BacktestRun[]>([])
const curve = ref<BacktestCurvePoint[]>([])
const metrics = ref<BacktestMetric[]>([])
const loading = ref(true)
const chartRef = ref<HTMLElement>()

onMounted(async () => {
  try {
    runs.value = await fetchBacktestRuns()
    if (runs.value[0]) await loadRun(runs.value[0].id)
  } finally {
    loading.value = false
  }
})

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
</script>

