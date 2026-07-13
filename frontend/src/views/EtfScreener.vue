<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>ETF 筛选</h2>
          <p class="section-note">从研究池中按收益、风险、交易性和数据质量筛出候选 ETF。</p>
        </div>
        <el-button type="primary" :loading="loading" @click="runScreen">开始筛选</el-button>
      </div>
      <el-form class="action-form" label-width="106px">
        <el-form-item label="筛选范围">
          <el-select v-model="form.scope">
            <el-option label="启用 ETF 池" value="enabled" />
            <el-option label="核心池" value="core" />
            <el-option label="当前持仓" value="positions" />
            <el-option label="目标组合" value="target" />
            <el-option label="定投相关" value="plans" />
            <el-option label="全部资产主表" value="all" />
            <el-option label="手动代码" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.scope === 'custom'" label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="多个代码用逗号或空格分隔" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-select v-model="rangeKey" @change="applyRange">
            <el-option label="最近 6 个月" value="6m" />
            <el-option label="最近 1 年" value="1y" />
            <el-option label="最近 3 年" value="3y" />
            <el-option label="最近 5 年" value="5y" />
            <el-option label="最近 10 年" value="10y" />
          </el-select>
          <span class="form-note">{{ form.start_date }} 至 {{ form.end_date }}</span>
        </el-form-item>
        <el-form-item label="最低样本">
          <el-input-number v-model="form.min_bars" :min="20" :max="2500" :step="20" />
        </el-form-item>
        <el-form-item label="最低交易性">
          <el-slider v-model="form.min_tradability_score" :min="0" :max="100" :step="5" />
        </el-form-item>
        <el-form-item label="最低买入分">
          <el-slider v-model="form.min_buy_score" :min="0" :max="100" :step="5" />
        </el-form-item>
        <el-form-item label="资产类别">
          <el-select v-model="form.asset_class" clearable placeholder="全部">
            <el-option label="权益" value="equity" />
            <el-option label="债券" value="bond" />
            <el-option label="货币现金" value="cash" />
            <el-option label="黄金/商品" value="gold" />
            <el-option label="跨境 QDII" value="qdii" />
          </el-select>
        </el-form-item>
        <el-form-item label="返回数量">
          <el-input-number v-model="form.limit" :min="10" :max="200" :step="10" />
        </el-form-item>
        <el-form-item label="自动补数">
          <el-switch v-model="form.auto_sync_missing" />
          <span class="form-note">适合手动代码少量评估；最多自动补 {{ form.max_auto_sync_symbols }} 只。</span>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-3"><div class="metric">候选总数<strong>{{ result?.total_candidates ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">返回数量<strong>{{ result?.returned ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">最高评分<strong>{{ topMetric?.buy_score ?? '-' }}</strong></div></section>
    <section class="panel span-3"><div class="metric">当前范围<strong>{{ scopeLabel }}</strong></div></section>

    <section class="panel span-12">
      <h2>候选排行</h2>
      <el-table :data="result?.metrics || []" height="620" empty-text="点击开始筛选生成候选 ETF">
        <el-table-column type="index" label="#" width="54" fixed />
        <el-table-column prop="symbol" label="代码" width="105" fixed />
        <el-table-column label="详情" width="76">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/etf-detail/${row.symbol}`)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column label="买入评分" width="130" sortable>
          <template #default="{ row }">
            <el-tag :type="buyScoreTag(row.buy_score)" size="small">{{ row.buy_score }} {{ row.buy_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="年化收益" width="110" sortable>
          <template #default="{ row }">{{ percent(row.annualized_return) }}</template>
        </el-table-column>
        <el-table-column label="最大回撤" width="110" sortable>
          <template #default="{ row }">{{ percent(row.max_drawdown) }}</template>
        </el-table-column>
        <el-table-column label="夏普" width="88" sortable>
          <template #default="{ row }">{{ numberValue(row.sharpe_ratio) }}</template>
        </el-table-column>
        <el-table-column label="卡玛" width="88" sortable>
          <template #default="{ row }">{{ numberValue(row.calmar_ratio) }}</template>
        </el-table-column>
        <el-table-column label="胜率" width="96">
          <template #default="{ row }">{{ percent(row.positive_day_rate) }}</template>
        </el-table-column>
        <el-table-column label="日均成交额" width="130">
          <template #default="{ row }">{{ money(row.average_amount) }}</template>
        </el-table-column>
        <el-table-column label="交易性" width="112">
          <template #default="{ row }">{{ row.tradability_score }} {{ row.tradability_level }}</template>
        </el-table-column>
        <el-table-column label="说明" min-width="240">
          <template #default="{ row }">{{ row.buy_notes.join('；') || row.tradability_notes.join('；') || '综合表现可用' }}</template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { screenEtfs, type EtfCompareMetric, type EtfScreenerResponse } from '../api/client'

const loading = ref(false)
const result = ref<EtfScreenerResponse | null>(null)
const symbolsText = ref('')
const rangeKey = ref('6m')

const form = reactive({
  scope: 'enabled',
  start_date: '',
  end_date: '',
  limit: 50,
  min_bars: 120,
  min_tradability_score: 50,
  min_buy_score: 45,
  asset_class: '',
  auto_sync_missing: false,
  max_auto_sync_symbols: 5,
})

onMounted(() => {
  applyRange()
  runScreen()
})

const topMetric = computed<EtfCompareMetric | null>(() => result.value?.metrics[0] || null)
const scopeLabel = computed(() => {
  const labels: Record<string, string> = {
    enabled: '启用池',
    core: '核心池',
    positions: '持仓',
    target: '目标',
    plans: '定投',
    all: '全部',
    custom: '手动',
  }
  return labels[form.scope] || form.scope
})

function applyRange() {
  const end = new Date()
  const start = new Date(end)
  const months: Record<string, number> = { '6m': 6, '1y': 12, '3y': 36, '5y': 60, '10y': 120 }
  start.setMonth(start.getMonth() - (months[rangeKey.value] || 36))
  form.start_date = formatDate(start)
  form.end_date = formatDate(end)
}

async function runScreen() {
  loading.value = true
  try {
    result.value = await screenEtfs({
      scope: form.scope,
      symbols: splitSymbols(),
      start_date: form.start_date,
      end_date: form.end_date,
      limit: form.limit,
      min_bars: form.min_bars,
      min_tradability_score: form.min_tradability_score,
      min_buy_score: form.min_buy_score,
      asset_class: form.asset_class || undefined,
      auto_sync_missing: form.auto_sync_missing,
      max_auto_sync_symbols: form.max_auto_sync_symbols,
    })
  } catch (error) {
    ElMessage.error(errorMessage(error, '筛选失败'))
  } finally {
    loading.value = false
  }
}

function splitSymbols() {
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
}

function formatDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function percent(value: string | null) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function numberValue(value: string | null) {
  if (value == null) return '-'
  return Number(value).toFixed(2)
}

function money(value: string | null) {
  if (value == null) return '-'
  const amount = Number(value)
  if (amount >= 100000000) return `${(amount / 100000000).toFixed(2)} 亿`
  if (amount >= 10000) return `${(amount / 10000).toFixed(2)} 万`
  return amount.toFixed(2)
}

function buyScoreTag(score: number) {
  if (score >= 75) return 'success'
  if (score >= 60) return 'info'
  if (score >= 45) return 'warning'
  return 'danger'
}

function errorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (detail) return detail
  return error instanceof Error ? error.message : fallback
}
</script>
