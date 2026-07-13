<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>数据更新与检查</h2>
        <el-button type="primary" :loading="actionLoading" @click="runFullDataFlow">一键更新并检查</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="日期模式">
          <el-radio-group v-model="dateMode" @change="applyPresetRange">
            <el-radio-button label="preset">快捷范围</el-radio-button>
            <el-radio-button label="custom">自定义日期</el-radio-button>
          </el-radio-group>
          <span class="form-note">当前：{{ dateRangeLabel }}</span>
        </el-form-item>
        <el-form-item v-if="dateMode === 'preset'" label="快捷范围">
          <el-select v-model="presetRange" @change="applyPresetRange">
            <el-option label="最近 1 个月（日常刷新）" value="1m" />
            <el-option label="最近 3 个月" value="3m" />
            <el-option label="最近 1 年（常用检查）" value="1y" />
            <el-option label="最近 3 年（策略观察）" value="3y" />
            <el-option label="最近 5 年（中长期回测）" value="5y" />
            <el-option label="最近 10 年（历史初始化）" value="10y" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" :clearable="false" />
        </el-form-item>
        <el-form-item label="同步范围">
          <el-select v-model="syncScope" @change="refreshSyncPlan">
            <el-option label="核心池：持仓 + 目标组合 + 定投 + 启用 ETF" value="core" />
            <el-option label="当前持仓" value="positions" />
            <el-option label="目标组合" value="target" />
            <el-option label="定投建议涉及 ETF" value="plans" />
            <el-option label="启用 ETF 池" value="enabled" />
            <el-option label="全部资产主表" value="all" />
          </el-select>
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="留空使用上方同步范围；手动输入则只同步这些代码" />
        </el-form-item>
        <el-form-item label="日历源">
          <el-select v-model="calendarSource">
            <el-option label="Tushare trade_cal" value="tushare" />
            <el-option label="AKShare" value="akshare" />
            <el-option label="Weekday fallback" value="weekday" />
          </el-select>
        </el-form-item>
        <el-form-item label="行情源">
          <el-select v-model="marketSource">
            <el-option label="Tushare fund_daily" value="tushare" />
            <el-option label="AKShare + Eastmoney fallback" value="akshare" />
            <el-option label="Eastmoney only" value="eastmoney" />
          </el-select>
        </el-form-item>
        <el-form-item label="同步数量">
          <el-input-number v-model="maxSymbols" :min="1" :max="50" />
          <span class="form-note">避免一次请求过久，默认先同步 10 只。</span>
        </el-form-item>
        <el-form-item label="请求间隔">
          <el-input-number v-model="requestIntervalSeconds" :min="0" :max="10" :step="0.5" />
          <span class="form-note">共享 Tushare 建议 1.5 秒或更高；AKShare 可设为 0。</span>
        </el-form-item>
        <el-form-item label="增量同步">
          <el-switch v-model="incrementalSync" />
          <span class="form-note">开启后优先只补库里缺失的最新区间，更省 Tushare 请求。</span>
        </el-form-item>
        <el-form-item label="使用提示" class="span-2">
          <div class="source-hint">
            <strong>{{ sourceHintTitle }}</strong>
            <p>{{ sourceHintText }}</p>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="actionLoading" @click="runCalendarSync">同步交易日历</el-button>
          <el-button :loading="actionLoading" @click="runMarketSync">同步行情</el-button>
          <el-button :loading="actionLoading" @click="runQualityCheck">检查缺失数据</el-button>
        </el-form-item>
      </el-form>
    </section>
    <section class="panel span-3"><div class="metric">整体状态<strong>{{ status?.status ?? '-' }}</strong></div></section>
    <section class="panel span-3"><div class="metric">错误数<strong>{{ status?.error_logs ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">警告数<strong>{{ status?.warning_logs ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">日志总数<strong>{{ status?.total_logs ?? 0 }}</strong></div></section>
    <section class="panel span-12">
      <div class="panel-header">
        <h2>本次行情同步计划</h2>
        <el-button :loading="loading" @click="refreshSyncPlan">刷新计划</el-button>
      </div>
      <div class="summary-grid">
        <div class="metric">同步范围<strong>{{ syncScopeLabel }}</strong></div>
        <div class="metric">计划 ETF<strong>{{ syncPlan?.total_symbols ?? 0 }}</strong></div>
        <div class="metric">缺行情<strong>{{ syncPlan?.missing_price_count ?? 0 }}</strong></div>
      </div>
      <el-table :data="syncPlan?.symbols ?? []" height="260">
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="来源" min-width="180">
          <template #default="{ row }">{{ formatCategories(row.categories) }}</template>
        </el-table-column>
        <el-table-column prop="latest_trade_date" label="最新行情日" width="130" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.has_clean_price ? 'success' : 'warning'">
              {{ row.has_clean_price ? '已有行情' : '待补行情' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
    <section class="panel span-12">
      <h2>数据质量日志</h2>
      <el-table :data="logs" height="560">
        <el-table-column prop="created_at" label="创建时间" width="190" />
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="trade_date" label="日期" width="130" />
        <el-table-column prop="check_type" label="检查项" width="180" />
        <el-table-column prop="severity" label="级别" width="120" />
        <el-table-column prop="message" label="说明" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  checkDataQuality,
  fetchDataQualityLogs,
  fetchDataQualityStatus,
  fetchMarketSyncPlan,
  syncCalendar,
  syncMarket,
  type DataQualityLog,
  type DataQualityStatus,
  type MarketSyncPlan,
} from '../api/client'

const status = ref<DataQualityStatus>()
const logs = ref<DataQualityLog[]>([])
const syncPlan = ref<MarketSyncPlan>()
const loading = ref(true)
const actionLoading = ref(false)
const today = formatDate(new Date())
const dateMode = ref<'preset' | 'custom'>('preset')
const presetRange = ref('1m')
const dateRange = ref<[string, string]>(buildPresetRange(presetRange.value))
const symbolsText = ref('')
const syncScope = ref('core')
const maxSymbols = ref(10)
const calendarSource = ref('tushare')
const marketSource = ref('tushare')
const requestIntervalSeconds = ref(1.5)
const incrementalSync = ref(true)

onMounted(refresh)

function applyPresetRange() {
  if (dateMode.value === 'preset') {
    dateRange.value = buildPresetRange(presetRange.value)
  }
}

async function refresh() {
  loading.value = true
  try {
    ;[status.value, logs.value, syncPlan.value] = await Promise.all([
      fetchDataQualityStatus(),
      fetchDataQualityLogs(),
      fetchMarketSyncPlan(syncScope.value),
    ])
  } finally {
    loading.value = false
  }
}

async function refreshSyncPlan() {
  syncPlan.value = await fetchMarketSyncPlan(syncScope.value)
}

async function runCalendarSync() {
  await withAction('交易日历同步完成', () =>
    syncCalendar({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      market: 'CN',
      source: calendarSource.value,
      incremental: incrementalSync.value,
    }),
  )
}

async function runMarketSync() {
  const symbols = splitSymbols()
  await withAction('行情同步完成', () =>
    syncMarket({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      symbols,
      sync_scope: symbols.length ? 'custom' : syncScope.value,
      source: marketSource.value,
      incremental: incrementalSync.value,
      max_symbols: maxSymbols.value,
      clean_after_sync: true,
      request_interval_seconds: requestIntervalSeconds.value,
    }),
  )
}

async function runQualityCheck() {
  const symbols = selectedQualitySymbols()
  if (!symbols.length) {
    ElMessage.warning('当前同步计划没有可检查的 ETF 代码')
    return
  }
  await withAction('缺失数据检查完成', () => checkDataQuality({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols }))
}

async function runFullDataFlow() {
  actionLoading.value = true
  try {
    await syncCalendar({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      market: 'CN',
      source: calendarSource.value,
      incremental: incrementalSync.value,
    })
    const symbols = splitSymbols()
    await syncMarket({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      symbols,
      sync_scope: symbols.length ? 'custom' : syncScope.value,
      source: marketSource.value,
      incremental: incrementalSync.value,
      max_symbols: maxSymbols.value,
      clean_after_sync: true,
      request_interval_seconds: requestIntervalSeconds.value,
    })
    const qualitySymbols = selectedQualitySymbols()
    if (qualitySymbols.length) await checkDataQuality({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols: qualitySymbols })
    ElMessage.success('数据更新流程已完成')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '执行失败')
  } finally {
    actionLoading.value = false
  }
}

async function withAction(successMessage: string, action: () => Promise<unknown>) {
  actionLoading.value = true
  try {
    await action()
    ElMessage.success(successMessage)
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '执行失败')
  } finally {
    actionLoading.value = false
  }
}

function splitSymbols() {
  return symbolsText.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
}

function selectedQualitySymbols() {
  const manual = splitSymbols()
  if (manual.length) return manual
  return syncPlan.value?.symbols.map((item) => item.symbol) ?? []
}

function formatCategories(categories: string[]) {
  const labels: Record<string, string> = {
    position: '持仓',
    target: '目标组合',
    plan: '定投',
    enabled: '启用池',
  }
  return categories.map((item) => labels[item] || item).join(' / ') || '-'
}

const syncScopeLabel = computed(() => {
  const labels: Record<string, string> = {
    core: '核心池',
    positions: '当前持仓',
    target: '目标组合',
    plans: '定投',
    enabled: '启用池',
    all: '全部资产',
  }
  return labels[syncScope.value] || syncScope.value
})

const dateRangeLabel = computed(() => `${dateRange.value[0]} 至 ${dateRange.value[1]}`)

function buildPresetRange(value: string): [string, string] {
  const end = new Date()
  const start = new Date(end)
  const monthMap: Record<string, number> = {
    '1m': 1,
    '3m': 3,
    '1y': 12,
    '3y': 36,
    '5y': 60,
    '10y': 120,
  }
  start.setMonth(start.getMonth() - (monthMap[value] || 1))
  return [formatDate(start), formatDate(end)]
}

function formatDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const sourceHintTitle = computed(() => {
  if (marketSource.value === 'tushare') return '共享 Tushare 建议'
  if (marketSource.value === 'akshare') return '开发与补数建议'
  return '备用源建议'
})

const sourceHintText = computed(() => {
  if (marketSource.value === 'tushare') {
    return incrementalSync.value
      ? '已开启增量同步，系统会优先只补最新缺口。先用较短日期范围和 1 到 5 只 ETF 验证，间隔建议保持在 1.5 秒以上。'
      : '当前是全量模式。先用较短日期范围和 1 到 5 只 ETF 验证，间隔建议保持在 1.5 秒以上，避免共享账号短时间请求过多。'
  }
  if (marketSource.value === 'akshare') {
    return '适合日常开发和大多数补数场景。若 AKShare 上游波动，系统会自动尝试 Eastmoney 备用源。'
  }
  return 'Eastmoney 适合作为备用数据源排障，不建议长期当作唯一正式来源。'
})
</script>
