<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>ETF 对比</h2>
          <p class="section-note">基于已清洗行情对比收益、波动、回撤、成交额、相关性和可交易性评分。</p>
        </div>
        <el-button type="primary" :loading="actionLoading" @click="runCompare">开始对比</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="多个代码用逗号或空格分隔，建议 2-5 只" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
      </el-form>
      <div class="source-hint">
        <strong>数据要求</strong>
        <p>本页只读取 `market_data_clean`。如果某只 ETF 样本不足，先到“数据健康”按代码同步行情，再回到这里对比。</p>
      </div>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <h2>标准化净值</h2>
        <div class="task-tags">
          <el-tag v-for="item in result?.metrics || []" :key="item.symbol" type="info">{{ item.symbol }}</el-tag>
        </div>
      </div>
      <div ref="chartRef" class="chart"></div>
    </section>

    <section class="panel span-4">
      <h2>可交易性提示</h2>
      <div class="insight-list">
        <div v-for="item in result?.metrics || []" :key="item.symbol" class="insight-item">
          <span>{{ item.symbol }} {{ item.name || '' }}</span>
          <strong>{{ item.tradability_score }} / {{ item.tradability_level }}</strong>
          <p>{{ item.tradability_notes.join('；') }}</p>
        </div>
      </div>
    </section>

    <section class="panel span-12">
      <h2>对比指标</h2>
      <el-table :data="result?.metrics || []" height="360" empty-text="请输入 ETF 代码后开始对比">
        <el-table-column prop="symbol" label="代码" width="100" fixed />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column label="总收益" width="110">
          <template #default="{ row }">{{ percent(row.total_return) }}</template>
        </el-table-column>
        <el-table-column label="年化收益" width="110">
          <template #default="{ row }">{{ percent(row.annualized_return) }}</template>
        </el-table-column>
        <el-table-column label="年化波动" width="110">
          <template #default="{ row }">{{ percent(row.annualized_volatility) }}</template>
        </el-table-column>
        <el-table-column label="最大回撤" width="110">
          <template #default="{ row }">{{ percent(row.max_drawdown) }}</template>
        </el-table-column>
        <el-table-column label="日均成交额" width="130">
          <template #default="{ row }">{{ money(row.average_amount) }}</template>
        </el-table-column>
        <el-table-column prop="bars" label="样本数" width="90" />
        <el-table-column label="可交易性" width="120">
          <template #default="{ row }">
            <el-tag :type="scoreTag(row.tradability_score)" size="small">{{ row.tradability_score }} {{ row.tradability_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="latest_trade_date" label="最新日期" width="120" />
      </el-table>
    </section>

    <section class="panel span-12">
      <h2>相关性矩阵</h2>
      <el-table :data="correlationRows" height="300">
        <el-table-column prop="symbol" label="代码" width="100" fixed />
        <el-table-column v-for="symbol in comparedSymbols" :key="symbol" :label="symbol" min-width="110">
          <template #default="{ row }">{{ row[symbol] }}</template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { compareEtfs, type EtfCompareResponse } from '../api/client'

const loading = ref(false)
const actionLoading = ref(false)
const chartRef = ref<HTMLElement>()
const result = ref<EtfCompareResponse | null>(null)
const today = new Date().toISOString().slice(0, 10)
const start = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([start, today])
const symbolsText = ref('510300,159915,513050')

onMounted(runCompare)

const comparedSymbols = computed(() => result.value?.metrics.map((item) => item.symbol) || [])
const correlationRows = computed(() =>
  comparedSymbols.value.map((symbol) => {
    const row: Record<string, string> = { symbol }
    for (const target of comparedSymbols.value) {
      const cell = result.value?.correlations.find((item) => item.symbol_x === symbol && item.symbol_y === target)
      row[target] = cell?.correlation == null ? '-' : Number(cell.correlation).toFixed(2)
    }
    return row
  }),
)

async function runCompare() {
  const symbols = splitSymbols()
  if (!symbols.length) {
    ElMessage.warning('请先输入 ETF 代码')
    return
  }
  actionLoading.value = true
  loading.value = true
  try {
    result.value = await compareEtfs({ symbols, start_date: dateRange.value[0], end_date: dateRange.value[1] })
    await nextTick()
    renderChart()
  } catch (error) {
    ElMessage.error(errorMessage(error, '对比失败'))
  } finally {
    actionLoading.value = false
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value || !result.value) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 48, right: 18, top: 48, bottom: 36 },
    xAxis: { type: 'category', data: firstSeriesDates() },
    yAxis: { type: 'value', scale: true },
    series: comparedSymbols.value.map((symbol) => ({
      name: symbol,
      type: 'line',
      smooth: true,
      symbolSize: 3,
      data: (result.value?.normalized_series[symbol] || []).map((item) => Number(item.value)),
    })),
  })
}

function firstSeriesDates() {
  const first = comparedSymbols.value.find((symbol) => (result.value?.normalized_series[symbol] || []).length > 0)
  return first ? (result.value?.normalized_series[first] || []).map((item) => item.trade_date) : []
}

function splitSymbols() {
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean).slice(0, 8)
}

function percent(value: string | null) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function money(value: string | null) {
  if (value == null) return '-'
  const amount = Number(value)
  if (amount >= 100000000) return `${(amount / 100000000).toFixed(2)} 亿`
  if (amount >= 10000) return `${(amount / 10000).toFixed(2)} 万`
  return amount.toFixed(2)
}

function scoreTag(score: number) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'info'
  if (score >= 40) return 'warning'
  return 'danger'
}

function errorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (detail) return detail
  return error instanceof Error ? error.message : fallback
}
</script>
