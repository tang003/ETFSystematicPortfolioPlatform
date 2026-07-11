<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>因子排名</h2>
        <el-button type="primary" :loading="actionLoading" @click="runFactorCalculation">计算因子</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="留空代表全部启用 ETF，多个代码用逗号分隔" />
        </el-form-item>
      </el-form>
      <el-table :data="factors" height="640">
        <el-table-column prop="symbol" label="代码" width="120" />
        <el-table-column label="详情" width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/etf-detail/${row.symbol}`)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="trade_date" label="日期" width="130" />
        <el-table-column prop="alpha_score" label="Alpha" width="120" sortable />
        <el-table-column prop="trend_score" label="趋势" width="120" />
        <el-table-column prop="momentum_score" label="动量" width="130" />
        <el-table-column prop="volatility_score" label="波动率" width="130" />
        <el-table-column prop="drawdown_score" label="回撤" width="130" />
        <el-table-column prop="liquidity_score" label="流动性" width="130" />
        <el-table-column label="可交易性" width="130">
          <template #default="{ row }">
            <el-tooltip :content="tradabilityNotes(row.symbol)" placement="top">
              <el-tag :type="scoreTagType(tradabilityScore(row.symbol))" size="small">
                {{ tradabilityScoreText(row.symbol) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { calculateFactors, fetchFactorRanking, scoreEtfTradability, type EtfCompareMetric, type Factor } from '../api/client'

const factors = ref<Factor[]>([])
const tradabilityMetrics = ref<Record<string, EtfCompareMetric>>({})
const loading = ref(true)
const actionLoading = ref(false)
const today = new Date().toISOString().slice(0, 10)
const lastYear = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([lastYear, today])
const symbolsText = ref('')

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    factors.value = await fetchFactorRanking()
    await refreshTradabilityScores()
  } finally {
    loading.value = false
  }
}

async function refreshTradabilityScores() {
  const symbols = Array.from(new Set(factors.value.map((item) => item.symbol)))
  if (!symbols.length) {
    tradabilityMetrics.value = {}
    return
  }
  try {
    const rows = await scoreEtfTradability({ symbols })
    tradabilityMetrics.value = Object.fromEntries(rows.map((item) => [item.symbol, item]))
  } catch {
    tradabilityMetrics.value = {}
  }
}

async function runFactorCalculation() {
  actionLoading.value = true
  try {
    await calculateFactors({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols: splitSymbols() })
    ElMessage.success('因子计算完成')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '因子计算失败')
  } finally {
    actionLoading.value = false
  }
}

function splitSymbols() {
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
}

function tradabilityScore(symbol: string) {
  const value = tradabilityMetrics.value[symbol]?.tradability_score
  return typeof value === 'number' ? value : null
}

function tradabilityScoreText(symbol: string) {
  const metric = tradabilityMetrics.value[symbol]
  if (!metric) return '未评分'
  return `${metric.tradability_score} ${metric.tradability_level}`
}

function tradabilityNotes(symbol: string) {
  const metric = tradabilityMetrics.value[symbol]
  if (!metric) return '暂无可交易性评分，请先同步行情。'
  return metric.tradability_notes.join('；')
}

function scoreTagType(value: number | null) {
  if (value === null) return 'info'
  if (value >= 80) return 'success'
  if (value >= 60) return 'info'
  if (value >= 40) return 'warning'
  return 'danger'
}
</script>
