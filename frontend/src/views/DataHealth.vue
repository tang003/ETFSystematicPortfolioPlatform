<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>数据更新与检查</h2>
        <el-button type="primary" :loading="actionLoading" @click="runFullDataFlow">一键更新并检查</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="分析周期">
          <el-segmented v-model="presetRange" :options="dataPresetOptions" @change="applyPresetRange" />
          <span class="form-note">{{ dateRangeLabel }}</span>
        </el-form-item>
        <el-form-item v-if="presetRange === 'custom'" label="日期范围">
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
          </el-select>
        </el-form-item>
        <el-form-item label="行情源">
          <el-select v-model="marketSource">
            <el-option label="Tushare fund_daily" value="tushare" />
          </el-select>
        </el-form-item>
        <el-form-item label="同步数量">
          <el-input-number v-model="maxSymbols" :min="1" :max="50" />
          <span class="form-note">避免一次请求过久，默认先同步 10 只。</span>
        </el-form-item>
        <el-form-item label="请求间隔">
          <el-input-number v-model="requestIntervalSeconds" :min="0" :max="10" :step="0.5" />
          <span class="form-note">当前已切换为 Tushare-only，建议共享 token 设置 1.5 秒或更高。</span>
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
    <section class="panel span-3"><div class="metric">最近状态<strong>{{ status?.status ?? '-' }}</strong><span>{{ latestBatchText }}</span></div></section>
    <section class="panel span-3"><div class="metric">最近错误<strong>{{ status?.error_logs ?? 0 }}</strong><span>历史累计 {{ status?.history_error_logs ?? 0 }}</span></div></section>
    <section class="panel span-3"><div class="metric">最近警告<strong>{{ status?.warning_logs ?? 0 }}</strong><span>历史累计 {{ status?.history_warning_logs ?? 0 }}</span></div></section>
    <section class="panel span-3"><div class="metric">最近日志<strong>{{ status?.total_logs ?? 0 }}</strong><span>历史累计 {{ status?.history_total_logs ?? 0 }}</span></div></section>
    <section class="panel span-12">
      <div class="panel-header">
        <h2>本次行情同步计划</h2>
        <el-button :loading="loading" @click="refreshSyncPlan">刷新计划</el-button>
      </div>
      <div class="summary-grid">
        <div class="metric">同步范围<strong>{{ syncScopeLabel }}</strong></div>
        <div class="metric">计划 ETF<strong>{{ syncPlan?.total_symbols ?? 0 }}</strong></div>
        <div class="metric">缺行情<strong>{{ syncPlan?.missing_price_count ?? 0 }}</strong></div>
        <div class="metric">策略可用<strong>{{ syncPlan?.ready_count ?? 0 }}</strong><span>门槛 {{ syncPlan?.min_bars ?? 120 }} 根</span></div>
        <div class="metric">样本不足<strong>{{ syncPlan?.insufficient_count ?? 0 }}</strong></div>
        <div class="metric">空行情<strong>{{ syncPlan?.empty_count ?? 0 }}</strong></div>
      </div>
      <el-table :data="syncPlan?.symbols ?? []" height="260">
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="来源" min-width="180">
          <template #default="{ row }">{{ formatCategories(row.categories) }}</template>
        </el-table-column>
        <el-table-column prop="latest_trade_date" label="最新行情日" width="130" />
        <el-table-column label="区间样本" width="120">
          <template #default="{ row }">
            {{ row.range_bar_count }} / {{ row.expected_bar_count ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="覆盖率" width="110">
          <template #default="{ row }">{{ formatPercent(row.coverage_ratio) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="sampleTagType(row.sample_status)">
              {{ sampleStatusLabel(row.sample_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sample_message" label="提示" min-width="240" />
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
import { buildPresetRange, dataPresetOptions, type DataPreset } from '../datePresets'

const status = ref<DataQualityStatus>()
const logs = ref<DataQualityLog[]>([])
const syncPlan = ref<MarketSyncPlan>()
const loading = ref(true)
const actionLoading = ref(false)
const presetRange = ref<DataPreset>('1m')
const dateRange = ref<[string, string]>(buildPresetRange(presetRange.value))
const symbolsText = ref('')
const syncScope = ref('core')
const maxSymbols = ref(10)
const calendarSource = ref('tushare')
const marketSource = ref('tushare')
const requestIntervalSeconds = ref(1.5)
const incrementalSync = ref(true)
const minBars = computed(() => {
  const days = Math.max(1, (new Date(dateRange.value[1]).getTime() - new Date(dateRange.value[0]).getTime()) / 86400000)
  if (days <= 120) return 40
  if (days <= 240) return 60
  if (days <= 540) return 120
  return 200
})

onMounted(refresh)

function applyPresetRange() {
  if (presetRange.value !== 'custom') {
    dateRange.value = buildPresetRange(presetRange.value)
  }
}

async function refresh() {
  loading.value = true
  try {
    ;[status.value, logs.value, syncPlan.value] = await Promise.all([
      fetchDataQualityStatus(),
      fetchDataQualityLogs(),
      fetchMarketSyncPlan(syncScope.value, syncPlanParams()),
    ])
  } finally {
    loading.value = false
  }
}

async function refreshSyncPlan() {
  syncPlan.value = await fetchMarketSyncPlan(syncScope.value, syncPlanParams())
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

function syncPlanParams() {
  return {
    start_date: dateRange.value[0],
    end_date: dateRange.value[1],
    min_bars: minBars.value,
  }
}

function formatPercent(value: number | null) {
  if (value == null) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function sampleStatusLabel(status: string) {
  const labels: Record<string, string> = {
    ready: '可用',
    insufficient: '样本不足',
    empty: '待补行情',
  }
  return labels[status] || status
}

function sampleTagType(status: string) {
  if (status === 'ready') return 'success'
  if (status === 'insufficient') return 'warning'
  return 'danger'
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
const latestBatchText = computed(() => (status.value?.latest_created_at ? `最近检查 ${status.value.latest_created_at}` : '暂无检查记录'))

const sourceHintTitle = computed(() => {
  return 'Tushare-only 建议'
})

const sourceHintText = computed(() => {
  return incrementalSync.value
    ? '已开启增量同步，系统只使用 Tushare 补最新缺口。先用较短日期范围和 1 到 5 只 ETF 验证，间隔建议保持在 1.5 秒以上。'
    : '当前是全量模式。系统只使用 Tushare，建议缩短日期范围并保留 1.5 秒以上请求间隔。'
})
</script>
