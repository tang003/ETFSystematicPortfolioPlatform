<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>{{ detail?.asset?.name || symbol }} 详情</h2>
          <p class="section-note">{{ symbol }} · {{ assetClassText(detail?.asset?.asset_class) }} · {{ regionText(detail?.asset?.asset_region) }}</p>
        </div>
        <div class="header-actions">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
          <el-button :loading="syncLoading" @click="syncCurrentEtf">同步本 ETF 行情</el-button>
          <el-button type="primary" :loading="loading" @click="refresh">刷新</el-button>
        </div>
      </div>
      <div class="summary-grid">
        <div class="metric">最新价格<strong>{{ detail?.metric.latest_close || '-' }}</strong></div>
        <div class="metric">总收益<strong>{{ percent(detail?.metric.total_return) }}</strong></div>
        <div class="metric">最大回撤<strong>{{ percent(detail?.metric.max_drawdown) }}</strong></div>
        <div class="metric">可交易性<strong>{{ tradabilityText }}</strong></div>
      </div>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <h2>净值与回撤</h2>
        <el-tag :type="scoreTag(detail?.metric.tradability_score ?? null)" size="small">{{ tradabilityText }}</el-tag>
      </div>
      <el-empty v-if="detail && !detail.curve.length" description="当前日期范围内没有本地清洗行情，请先同步本 ETF 行情" />
      <div v-show="detail?.curve.length" ref="chartRef" class="chart"></div>
    </section>

    <section class="panel span-4">
      <h2>资产画像</h2>
      <div class="insight-list">
        <div class="insight-item">
          <span>样本数</span>
          <strong>{{ detail?.metric.bars || 0 }}</strong>
          <p>区间：{{ detail?.metric.first_trade_date || '-' }} 至 {{ detail?.metric.latest_trade_date || '-' }}</p>
        </div>
        <div class="insight-item">
          <span>日均成交额</span>
          <strong>{{ money(detail?.metric.average_amount) }}</strong>
          <p>{{ detail?.metric.tradability_notes.join('；') || '暂无评分说明' }}</p>
        </div>
        <div class="insight-item">
          <span>年化波动</span>
          <strong>{{ percent(detail?.metric.annualized_volatility) }}</strong>
          <p>风险等级：{{ detail?.asset?.risk_level ? `R${detail.asset.risk_level}` : '-' }}</p>
        </div>
      </div>
    </section>

    <section class="panel span-5">
      <h2>最新因子</h2>
      <el-table :data="factorRows" height="300">
        <el-table-column prop="name" label="指标" min-width="120" />
        <el-table-column prop="value" label="数值" min-width="120" />
      </el-table>
    </section>

    <section class="panel span-7">
      <h2>最近行情</h2>
      <el-table :data="detail?.recent_bars || []" height="300">
        <el-table-column prop="trade_date" label="日期" width="120" />
        <el-table-column prop="open" label="开盘" width="100" />
        <el-table-column prop="close" label="收盘" width="100" />
        <el-table-column label="成交额" width="130">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="data_status" label="状态" width="100" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchEtfDetail, syncMarket, type EtfDetailResponse } from '../api/client'

const route = useRoute()
const symbol = computed(() => String(route.params.symbol || ''))
const detail = ref<EtfDetailResponse | null>(null)
const loading = ref(false)
const syncLoading = ref(false)
const chartRef = ref<HTMLElement>()
const today = new Date().toISOString().slice(0, 10)
const start = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([start, today])

onMounted(refresh)

const tradabilityText = computed(() => {
  if (!detail.value) return '-'
  return `${detail.value.metric.tradability_score} ${detail.value.metric.tradability_level}`
})

const factorRows = computed(() => {
  const factor = detail.value?.latest_factor
  if (!factor) return []
  return [
    { name: 'Alpha', value: factor.alpha_score || '-' },
    { name: '趋势', value: factor.trend_score || '-' },
    { name: '动量', value: factor.momentum_score || '-' },
    { name: '波动', value: factor.volatility_score || '-' },
    { name: '回撤', value: factor.drawdown_score || '-' },
    { name: '流动性', value: factor.liquidity_score || '-' },
  ]
})

async function refresh() {
  if (!symbol.value) return
  loading.value = true
  try {
    detail.value = await fetchEtfDetail(symbol.value, { start_date: dateRange.value[0], end_date: dateRange.value[1] })
    await nextTick()
    renderChart()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载 ETF 详情失败')
  } finally {
    loading.value = false
  }
}

async function syncCurrentEtf() {
  if (!symbol.value) return
  syncLoading.value = true
  try {
    await syncMarket({
      symbols: [symbol.value],
      sync_scope: 'custom',
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      source: 'akshare',
      incremental: true,
      max_symbols: 1,
      clean_after_sync: true,
      request_interval_seconds: 0,
    })
    ElMessage.success('已同步本 ETF 行情')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同步本 ETF 行情失败')
  } finally {
    syncLoading.value = false
  }
}

function renderChart() {
  if (!chartRef.value || !detail.value?.curve.length) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 48, right: 18, top: 48, bottom: 36 },
    xAxis: { type: 'category', data: detail.value.curve.map((item) => item.trade_date) },
    yAxis: [
      { type: 'value', scale: true, name: '净值' },
      { type: 'value', scale: true, name: '回撤' },
    ],
    series: [
      { name: '标准化净值', type: 'line', smooth: true, data: detail.value.curve.map((item) => Number(item.normalized_value)), symbolSize: 3 },
      { name: '回撤', type: 'line', smooth: true, yAxisIndex: 1, data: detail.value.curve.map((item) => Number(item.drawdown) * 100), symbolSize: 3 },
    ],
  })
}

function percent(value: string | null | undefined) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function money(value: string | null | undefined) {
  if (value == null) return '-'
  const amount = Number(value)
  if (amount >= 100000000) return `${(amount / 100000000).toFixed(2)} 亿`
  if (amount >= 10000) return `${(amount / 10000).toFixed(2)} 万`
  return amount.toFixed(2)
}

function scoreTag(score: number | null) {
  if (score == null) return 'info'
  if (score >= 80) return 'success'
  if (score >= 60) return 'info'
  if (score >= 40) return 'warning'
  return 'danger'
}

function assetClassText(value: string | null | undefined) {
  const map: Record<string, string> = { equity: '权益', bond: '债券', gold: '黄金', commodity: '商品', cash: '货币', qdii: 'QDII' }
  return map[value || ''] || value || '-'
}

function regionText(value: string | null | undefined) {
  const map: Record<string, string> = { CN: '中国内地', HK: '港股', US: '美国', GLOBAL: '全球', CN_HK_US: '中概/港美' }
  return map[value || ''] || value || '-'
}
</script>
