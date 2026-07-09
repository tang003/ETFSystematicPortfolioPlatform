<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-5">
      <h2>目标权重</h2>
      <div ref="chartRef" class="chart"></div>
    </section>
    <section class="panel span-7">
      <div class="panel-header">
        <h2>目标组合</h2>
        <el-button type="primary" :loading="actionLoading" @click="runStrategyFlow">运行策略</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="策略代码">
          <el-input v-model="strategyCode" />
        </el-form-item>
        <el-form-item label="运行日期">
          <el-date-picker v-model="runDate" type="date" value-format="YYYY-MM-DD" placeholder="默认今天" />
        </el-form-item>
      </el-form>
      <el-table :data="targets" height="360">
        <el-table-column prop="run_id" label="运行 ID" width="90" />
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="asset_class" label="类别" width="120" />
        <el-table-column prop="raw_target_weight" label="原始权重" width="120" />
        <el-table-column prop="final_target_weight" label="最终权重" width="120" />
        <el-table-column prop="reason" label="说明" min-width="240" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchTargetPortfolio, runStrategy, type TargetPortfolio } from '../api/client'

const targets = ref<TargetPortfolio[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const chartRef = ref<HTMLElement>()
const strategyCode = ref('core_etf_rotation')
const runDate = ref(new Date().toISOString().slice(0, 10))

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    targets.value = await fetchTargetPortfolio()
    await nextTick()
    renderChart()
  } finally {
    loading.value = false
  }
}

async function runStrategyFlow() {
  actionLoading.value = true
  try {
    const result = await runStrategy({ strategy_code: strategyCode.value, run_date: runDate.value, run_type: 'manual' })
    ElMessage.success(`策略运行完成，run_id=${String(result.run_id ?? '-')}`)
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '策略运行失败')
  } finally {
    actionLoading.value = false
  }
}

function renderChart() {
  if (!chartRef.value) return
  echarts.init(chartRef.value).setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: '70%', data: targets.value.map((item) => ({ name: item.symbol, value: Number(item.final_target_weight ?? 0) })) }],
  })
}
</script>
