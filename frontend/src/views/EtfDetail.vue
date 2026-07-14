<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12 decision-panel">
      <div class="panel-header">
        <div>
          <h2>{{ detail?.asset?.name || symbol }} ETF 详情 / 买入评估</h2>
          <p class="section-note">
            {{ symbol }} · {{ assetClassText(detail?.asset?.asset_class) }} · {{ regionText(detail?.asset?.asset_region) }}；
            分析周期是历史回看窗口，不等于计划持有周期。
          </p>
        </div>
        <div class="header-actions">
          <div class="control-group">
            <span>分析周期</span>
            <el-segmented v-model="rangeKey" :options="rangeOptions" @change="applyRange" />
          </div>
          <div class="control-group">
            <span>计划持有</span>
            <el-segmented v-model="holdingPeriod" :options="holdingOptions" />
          </div>
          <el-date-picker
            v-if="rangeKey === 'custom'"
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="refresh"
          />
          <el-button :loading="syncLoading" @click="syncCurrentEtf">同步本 ETF 行情</el-button>
          <el-button type="primary" :loading="loading" @click="refresh">刷新</el-button>
        </div>
      </div>

      <div class="decision-grid">
        <div class="decision-main">
          <span>系统结论</span>
          <strong>{{ detail?.decision.action || '-' }}</strong>
          <p>{{ detail?.decision.position_hint || '请选择 ETF 并刷新数据。' }}</p>
        </div>
        <div class="decision-score">
          <span>买入评分</span>
          <strong>{{ detail?.decision.score ?? '-' }}</strong>
          <el-tag :type="scoreTag(detail?.decision.score ?? null)" size="small">
            {{ detail?.decision.level || '-' }} · 置信度 {{ detail?.decision.confidence || '-' }}
          </el-tag>
        </div>
        <div class="decision-card">
          <span>买入节奏</span>
          <p>{{ detail?.decision.entry_plan || '-' }}</p>
        </div>
        <div class="decision-card">
          <span>计划持有：{{ holdingPeriodText }}</span>
          <p>{{ holdingPlanText }}</p>
        </div>
        <div class="decision-card">
          <span>风险阈值</span>
          <p>{{ detail?.decision.stop_loss_hint || '-' }}</p>
        </div>
      </div>

      <div class="summary-grid">
        <div class="metric">最新价格<strong>{{ detail?.metric.latest_close || '-' }}</strong><span>{{ detail?.metric.latest_trade_date || '-' }}</span></div>
        <div class="metric">分析周期收益<strong :class="profitClass(detail?.metric.total_return)">{{ percent(detail?.metric.total_return) }}</strong><span>{{ rangeLabel }}</span></div>
        <div class="metric">年化收益<strong :class="profitClass(detail?.metric.annualized_return)">{{ percent(detail?.metric.annualized_return) }}</strong><span>用于和波动、回撤一起看</span></div>
        <div class="metric">最大回撤<strong class="profit-down">{{ percent(detail?.metric.max_drawdown) }}</strong><span>回撤越深，仓位越要保守</span></div>
        <div class="metric">夏普比率<strong>{{ numberText(detail?.metric.sharpe_ratio) }}</strong><span>风险调整后收益，越高越好</span></div>
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
      <h2>关键解释</h2>
      <div class="insight-list">
        <div class="insight-item">
          <span>为什么是这个结论</span>
          <ul>
            <li v-for="item in detail?.decision.reasons || []" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div class="insight-item">
          <span>主要风险</span>
          <ul>
            <li v-for="item in detail?.decision.risks || []" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div class="insight-item">
          <span>下一步</span>
          <ul>
            <li v-for="item in detail?.decision.next_steps || []" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel span-5">
      <h2>ETF 主资料</h2>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="基金公司">{{ detail?.asset?.fund_company || '-' }}</el-descriptions-item>
        <el-descriptions-item label="跟踪指数">{{ detail?.asset?.tracking_index || '-' }}</el-descriptions-item>
        <el-descriptions-item label="上市日期">{{ detail?.asset?.listing_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="基金规模">{{ fundSizeText(detail?.asset?.fund_size) }}</el-descriptions-item>
        <el-descriptions-item label="管理费">{{ feeText(detail?.asset?.management_fee) }}</el-descriptions-item>
        <el-descriptions-item label="托管费">{{ feeText(detail?.asset?.custody_fee) }}</el-descriptions-item>
        <el-descriptions-item label="综合费率">{{ feeText(detail?.asset?.expense_ratio ?? totalFee) }}</el-descriptions-item>
        <el-descriptions-item label="跟踪误差">{{ percent(detail?.asset?.tracking_error) }}</el-descriptions-item>
        <el-descriptions-item label="最新溢价率">{{ percent(detail?.asset?.latest_premium_rate) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="panel span-7">
      <div class="panel-header">
        <div>
          <h2>量化体检</h2>
          <p class="section-note">把收益、风险、交易性和数据质量放在一起看；单个指标不能单独决定买卖。</p>
        </div>
      </div>
      <el-table :data="quantRows" height="320">
        <el-table-column prop="name" label="维度" width="130" />
        <el-table-column prop="value" label="当前值" width="130" />
        <el-table-column prop="explain" label="说明" min-width="220" />
      </el-table>
    </section>

    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>同指数 ETF 替代</h2>
          <p class="section-note">同样跟踪一个指数时，优先比较规模、费率、成交额和数据质量；这里用于人工选择，不会自动交易。</p>
        </div>
      </div>
      <el-empty v-if="detail && !detail.alternatives.length" description="暂无同指数 ETF 候选；可先补全 ETF 主资料中的跟踪指数" />
      <el-table v-else :data="detail?.alternatives || []" height="300">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="fund_company" label="基金公司" min-width="130" />
        <el-table-column label="推荐" width="110">
          <template #default="{ row }">
            <el-tag :type="alternativeTag(row.recommendation_level)" size="small">{{ row.recommendation_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="recommendation_score" label="综合分" width="90" />
        <el-table-column prop="tradability_score" label="交易性" width="90" />
        <el-table-column label="规模" width="120">
          <template #default="{ row }">{{ fundSizeText(row.fund_size) }}</template>
        </el-table-column>
        <el-table-column label="费率" width="100">
          <template #default="{ row }">{{ feeText(row.expense_ratio) }}</template>
        </el-table-column>
        <el-table-column label="日均成交额" width="130">
          <template #default="{ row }">{{ money(row.average_amount) }}</template>
        </el-table-column>
        <el-table-column label="原因" min-width="240">
          <template #default="{ row }">{{ row.reasons.join('；') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/etf-detail/${row.symbol}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>原始行情抽样</h2>
          <p class="section-note">主要用于排查数据是否同步和清洗正常；普通买入决策优先看上方结论、量化体检和同指数替代。</p>
        </div>
      </div>
      <el-table :data="detail?.recent_bars || []" height="300">
        <el-table-column prop="trade_date" label="日期" width="120" />
        <el-table-column prop="open" label="开盘" width="100" />
        <el-table-column prop="close" label="收盘" width="100" />
        <el-table-column label="成交额" width="140">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="data_status" label="状态" width="120" />
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
import { analysisPresetOptions, buildPresetRange, presetLabel, type AnalysisPreset } from '../datePresets'

const route = useRoute()
const symbol = computed(() => String(route.params.symbol || ''))
const detail = ref<EtfDetailResponse | null>(null)
const loading = ref(false)
const syncLoading = ref(false)
const chartRef = ref<HTMLElement>()
const rangeKey = ref<AnalysisPreset>('6m')
const rangeOptions = analysisPresetOptions
const holdingPeriod = ref('6m')
const holdingOptions = [
  { label: '1个月', value: '1m' },
  { label: '3个月', value: '3m' },
  { label: '6个月', value: '6m' },
  { label: '1年+', value: '1y' },
]
const dateRange = ref<[string, string]>(buildPresetRange('6m'))

onMounted(refresh)

const tradabilityText = computed(() => {
  if (!detail.value) return '-'
  return `${detail.value.metric.tradability_score} ${detail.value.metric.tradability_level}`
})

const rangeLabel = computed(() => `${presetLabel(rangeKey.value)}：${dateRange.value[0]} 至 ${dateRange.value[1]}`)
const holdingPeriodText = computed(() => {
  const item = holdingOptions.find((option) => option.value === holdingPeriod.value)
  return item?.label || holdingPeriod.value
})

const totalFee = computed(() => {
  const asset = detail.value?.asset
  if (!asset) return null
  const management = asset.management_fee ? Number(asset.management_fee) : 0
  const custody = asset.custody_fee ? Number(asset.custody_fee) : 0
  return management || custody ? management + custody : null
})

const holdingPlanText = computed(() => {
  const score = detail.value?.decision.score ?? 0
  if (holdingPeriod.value === '1m') return '1 个月更偏交易观察，当前系统只给 ETF 投研建议，不适合据此频繁短炒。'
  if (holdingPeriod.value === '3m') return score >= 60 ? '3 个月可小额分批验证趋势，若回撤扩大应暂停加仓。' : '3 个月窗口较短，评分不足时建议只观察不建仓。'
  if (holdingPeriod.value === '6m') return score >= 60 ? '6 个月适合按月分批，重点跟踪回撤、成交额和同指数替代。' : '6 个月持有也需要先等评分或数据质量改善。'
  return score >= 60 ? '1 年以上更适合配置思路，建议纳入目标组合并控制单 ETF 权重。' : '长期持有前需要先确认指数逻辑、费率、规模和数据完整性。'
})

const quantRows = computed(() => {
  const metric = detail.value?.metric
  const factor = detail.value?.latest_factor
  if (!metric) return []
  return [
    { name: '收益', value: percent(metric.total_return), explain: `分析周期 ${rangeLabel.value} 的累计收益。` },
    { name: '年化收益', value: percent(metric.annualized_return), explain: '把当前区间收益折算成年化，样本越长越有参考意义。' },
    { name: '波动', value: percent(metric.annualized_volatility), explain: '年化波动越高，持有过程越容易出现大幅浮亏。' },
    { name: '最大回撤', value: percent(metric.max_drawdown), explain: '历史最差从高点回落幅度，是仓位控制的重要参考。' },
    { name: '夏普', value: numberText(metric.sharpe_ratio), explain: '风险调整后收益，通常要和同类 ETF 横向比较。' },
    { name: '交易性', value: `${metric.tradability_score} ${metric.tradability_level}`, explain: metric.tradability_notes.join('；') || '成交额和样本质量可用。' },
    { name: '数据质量', value: `${metric.bars} 条`, explain: detail.value?.decision.data_quality || '暂无数据质量说明。' },
    { name: 'Alpha', value: factor?.alpha_score || '-', explain: '本地因子综合分，用于排序参考，不单独构成买入理由。' },
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
      source: 'tushare',
      incremental: true,
      max_symbols: 1,
      clean_after_sync: true,
      request_interval_seconds: 0.2,
    })
    ElMessage.success('已同步本 ETF 行情')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同步本 ETF 行情失败')
  } finally {
    syncLoading.value = false
  }
}

function applyRange() {
  if (rangeKey.value === 'custom') return
  dateRange.value = buildPresetRange(rangeKey.value)
  void refresh()
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

function percent(value: string | number | null | undefined) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function numberText(value: string | number | null | undefined) {
  if (value == null) return '-'
  return Number(value).toFixed(2)
}

function feeText(value: string | number | null | undefined) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(3)}%`
}

function money(value: string | null | undefined) {
  if (value == null) return '-'
  const amount = Number(value)
  if (amount >= 100000000) return `${(amount / 100000000).toFixed(2)} 亿`
  if (amount >= 10000) return `${(amount / 10000).toFixed(2)} 万`
  return amount.toFixed(2)
}

function fundSizeText(value: string | null | undefined) {
  if (!value) return '-'
  return `${(Number(value) / 100000000).toFixed(2)} 亿`
}

function scoreTag(score: number | null) {
  if (score == null) return 'info'
  if (score >= 80) return 'success'
  if (score >= 60) return 'info'
  if (score >= 40) return 'warning'
  return 'danger'
}

function profitClass(value: string | number | null | undefined) {
  if (value == null) return ''
  return Number(value) >= 0 ? 'profit-up' : 'profit-down'
}

function alternativeTag(level: string) {
  if (level.includes('首选')) return 'success'
  if (level.includes('可替代')) return 'info'
  return 'warning'
}

function assetClassText(value: string | null | undefined) {
  const map: Record<string, string> = { equity: '权益', bond: '债券', gold: '黄金', commodity: '商品', cash: '货币', qdii: 'QDII' }
  return map[value || ''] || value || '-'
}

function regionText(value: string | null | undefined) {
  const map: Record<string, string> = { CN: '中国内地', HK: '港股', US: '美国', GLOBAL: '全球', CN_HK_US: '中概/港美', JP: '日本', DE: '德国' }
  return map[value || ''] || value || '-'
}
</script>
