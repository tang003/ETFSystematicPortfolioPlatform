<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>录入当前持仓</h2>
          <p class="section-note">只需填写代码、持仓数量和成本价；名称、类型、现价由系统根据资产池和最新行情自动补全。</p>
        </div>
        <div class="header-actions">
          <el-button @click="addRow">新增一行</el-button>
          <el-button :loading="actionLoading" @click="resolveRows">自动补全</el-button>
          <el-button type="primary" :loading="actionLoading" @click="saveSnapshot">保存持仓快照</el-button>
          <el-button type="success" :loading="actionLoading" @click="runAnalysis">运行持仓分析</el-button>
        </div>
      </div>

      <el-form class="action-form" label-width="92px">
        <el-form-item label="快照日期">
          <el-date-picker v-model="positionDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="运行 ID">
          <el-input-number v-model="runId" :min="1" />
          <span class="form-note">用于和某次目标组合对比；通常填最近一次策略运行 ID。</span>
        </el-form-item>
      </el-form>

      <div class="summary-grid">
        <div class="metric">总市值<strong>{{ formatMoney(draftSummary.marketValue) }}</strong></div>
        <div class="metric">总成本<strong>{{ formatMoney(draftSummary.costBasis) }}</strong></div>
        <div class="metric">持仓盈亏<strong :class="profitClass(draftSummary.pnl)">{{ formatMoney(draftSummary.pnl) }}</strong></div>
        <div class="metric">收益率<strong :class="profitClass(draftSummary.pnl)">{{ formatPercent(draftSummary.pnlRate) }}</strong></div>
      </div>

      <el-alert
        class="table-hint"
        type="info"
        :closable="false"
        show-icon
        title="如果名称或现价为空，先点击自动补全；仍为空说明该代码还没有进入资产池或尚未同步行情。"
      />

      <el-table :data="draftRows" height="380">
        <el-table-column label="代码" width="130">
          <template #default="{ row }">
            <el-input v-model="row.symbol" placeholder="513050" @change="resolveRows" />
          </template>
        </el-table-column>
        <el-table-column label="持仓数量" width="150">
          <template #default="{ row }"><el-input-number v-model="row.quantity" :min="0" :step="100" /></template>
        </el-table-column>
        <el-table-column label="成本价" width="130">
          <template #default="{ row }"><el-input-number v-model="row.cost_price" :min="0" :precision="3" :step="0.001" /></template>
        </el-table-column>
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }">{{ row.position_name || '待补全' }}</template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }"><el-tag size="small">{{ assetTypeText(row.asset_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="现价" width="120">
          <template #default="{ row }">{{ row.current_price ? formatPrice(row.current_price) : '-' }}</template>
        </el-table-column>
        <el-table-column label="价格日期" width="120">
          <template #default="{ row }">{{ row.price_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="市值" width="130">
          <template #default="{ row }">{{ formatMoney(rowMarketValue(row)) }}</template>
        </el-table-column>
        <el-table-column label="持仓成本" width="130">
          <template #default="{ row }">{{ formatMoney(rowCostBasis(row)) }}</template>
        </el-table-column>
        <el-table-column label="盈亏" width="120">
          <template #default="{ row }">
            <span :class="profitClass(rowPnl(row))">{{ formatMoney(rowPnl(row)) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="170">
          <template #default="{ row }">
            <el-tag v-if="row.resolved" size="small" type="success">已补全</el-tag>
            <span v-else class="muted">{{ row.resolve_message || '等待补全' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ $index }"><el-button text type="danger" @click="removeRow($index)">删除</el-button></template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-5">
      <h2>当前持仓权重</h2>
      <el-table :data="positions" height="360">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column label="名称" min-width="120">
          <template #default="{ row }">{{ row.position_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }"><el-tag size="small">{{ assetTypeText(row.asset_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="市值" width="130">
          <template #default="{ row }">{{ formatMoney(Number(row.market_value || 0)) }}</template>
        </el-table-column>
        <el-table-column label="权重" width="100">
          <template #default="{ row }">{{ formatPercent(Number(row.weight || 0)) }}</template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-7">
      <h2>持仓分析结果</h2>
      <el-table :data="analysis" height="360">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column label="建议" width="120">
          <template #default="{ row }"><el-tag :type="tagType(row.action_suggestion)">{{ actionText(row.action_suggestion) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="当前权重" width="110">
          <template #default="{ row }">{{ formatPercent(Number(row.current_weight || 0)) }}</template>
        </el-table-column>
        <el-table-column label="目标权重" width="110">
          <template #default="{ row }">{{ formatPercent(Number(row.target_weight || 0)) }}</template>
        </el-table-column>
        <el-table-column label="差异" width="100">
          <template #default="{ row }">{{ formatPercent(Number(row.weight_diff || 0)) }}</template>
        </el-table-column>
        <el-table-column prop="alpha_score" label="Alpha" width="100" />
        <el-table-column prop="reason" label="原因" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  analyzeHoldings,
  fetchHoldingAnalysis,
  fetchPositions,
  resolvePositionSymbols,
  savePositionSnapshot,
  type HoldingAnalysis,
  type PortfolioPosition,
} from '../api/client'

interface DraftPosition {
  symbol: string
  position_name: string
  asset_type: 'etf' | 'stock' | 'cash' | 'other'
  quantity: number
  current_price: number
  cost_price: number
  price_date: string
  resolved: boolean
  resolve_message: string
}

const loading = ref(false)
const actionLoading = ref(false)
const positionDate = ref(new Date().toISOString().slice(0, 10))
const runId = ref(1)
const positions = ref<PortfolioPosition[]>([])
const analysis = ref<HoldingAnalysis[]>([])
const draftRows = ref<DraftPosition[]>([emptyRow()])

const draftSummary = computed(() => {
  const marketValue = draftRows.value.reduce((sum, row) => sum + rowMarketValue(row), 0)
  const costBasis = draftRows.value.reduce((sum, row) => sum + rowCostBasis(row), 0)
  const pnl = marketValue - costBasis
  return {
    marketValue,
    costBasis,
    pnl,
    pnlRate: costBasis > 0 ? pnl / costBasis : 0,
  }
})

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    ;[positions.value, analysis.value] = await Promise.all([fetchPositions(), fetchHoldingAnalysis()])
    if (positions.value.length) {
      draftRows.value = positions.value.map((item) => ({
        symbol: item.symbol,
        position_name: item.position_name || '',
        asset_type: normalizeAssetType(item.asset_type),
        quantity: Number(item.quantity || 0),
        current_price: Number(item.current_price || 0),
        cost_price: Number(item.cost_price || 0),
        price_date: item.position_date,
        resolved: Boolean(item.position_name && item.current_price),
        resolve_message: '',
      }))
    }
  } finally {
    loading.value = false
  }
}

function emptyRow(): DraftPosition {
  return {
    symbol: '',
    position_name: '',
    asset_type: 'etf',
    quantity: 0,
    current_price: 0,
    cost_price: 0,
    price_date: '',
    resolved: false,
    resolve_message: '',
  }
}

function addRow() {
  draftRows.value.push(emptyRow())
}

function removeRow(index: number) {
  draftRows.value.splice(index, 1)
}

async function resolveRows() {
  const symbols = draftRows.value.map((row) => row.symbol.trim()).filter(Boolean)
  if (!symbols.length) {
    ElMessage.warning('请先填写代码')
    return
  }
  actionLoading.value = true
  try {
    const details = await resolvePositionSymbols(symbols)
    const detailMap = new Map(details.map((item) => [item.symbol, item]))
    draftRows.value = draftRows.value.map((row) => {
      const symbol = row.symbol.trim()
      const detail = detailMap.get(symbol)
      if (!detail) return row
      return {
        ...row,
        symbol,
        position_name: detail.position_name || row.position_name,
        asset_type: normalizeAssetType(detail.asset_type),
        current_price: Number(detail.current_price || 0),
        price_date: detail.price_date || '',
        resolved: detail.resolved,
        resolve_message: detail.message || '',
      }
    })
    const unresolvedCount = details.filter((item) => !item.resolved).length
    if (unresolvedCount) {
      ElMessage.warning(`${unresolvedCount} 个代码未完全补全，请检查资产池或行情同步状态`)
    } else {
      ElMessage.success('名称、类型和现价已补全')
    }
  } catch (error) {
    ElMessage.error(errorMessage(error, '补全失败'))
  } finally {
    actionLoading.value = false
  }
}

async function saveSnapshot() {
  actionLoading.value = true
  try {
    const rows = draftRows.value
      .filter((row) => row.symbol.trim() && Number(row.quantity || 0) > 0)
      .map((row) => ({
        symbol: row.symbol.trim(),
        quantity: row.quantity,
        cost_price: row.cost_price,
      }))
    if (!rows.length) {
      ElMessage.warning('请至少填写一条有效持仓')
      return
    }
    positions.value = await savePositionSnapshot({ position_date: positionDate.value, positions: rows })
    ElMessage.success('持仓快照已保存')
    await refresh()
  } catch (error) {
    ElMessage.error(errorMessage(error, '保存失败'))
  } finally {
    actionLoading.value = false
  }
}

async function runAnalysis() {
  actionLoading.value = true
  try {
    analysis.value = await analyzeHoldings({ run_id: runId.value, analysis_date: positionDate.value })
    ElMessage.success('持仓分析完成')
  } catch (error) {
    ElMessage.error(errorMessage(error, '分析失败'))
  } finally {
    actionLoading.value = false
  }
}

function rowMarketValue(row: DraftPosition) {
  return roundMoney(Number(row.quantity || 0) * Number(row.current_price || 0))
}

function rowCostBasis(row: DraftPosition) {
  return roundMoney(Number(row.quantity || 0) * Number(row.cost_price || 0))
}

function rowPnl(row: DraftPosition) {
  return roundMoney(rowMarketValue(row) - rowCostBasis(row))
}

function roundMoney(value: number) {
  return Math.round(value * 100) / 100
}

function formatMoney(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPrice(value: number) {
  return Number(value || 0).toFixed(3)
}

function formatPercent(value: number) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`
}

function profitClass(value: number) {
  if (value > 0) return 'profit-up'
  if (value < 0) return 'profit-down'
  return ''
}

function normalizeAssetType(value: string | null): DraftPosition['asset_type'] {
  if (value === 'stock' || value === 'cash' || value === 'other') return value
  return 'etf'
}

function assetTypeText(value: string | null) {
  const map: Record<string, string> = {
    etf: 'ETF/基金',
    stock: '股票',
    cash: '现金',
    other: '其他',
  }
  return map[value || 'etf'] || value || 'ETF/基金'
}

function actionText(action: string) {
  const map: Record<string, string> = {
    ADD: '加仓',
    REDUCE: '减仓',
    HOLD: '持有',
    REDUCE_OR_EXIT: '减仓/退出',
  }
  return map[action] || action
}

function tagType(action: string) {
  if (action === 'ADD') return 'success'
  if (action === 'REDUCE' || action === 'REDUCE_OR_EXIT') return 'warning'
  return 'info'
}

function errorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (detail) return detail
  return error instanceof Error ? error.message : fallback
}
</script>
