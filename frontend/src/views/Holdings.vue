<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>录入当前持仓</h2>
          <p class="section-note">通过弹窗维护持仓；新增、编辑和补仓确认后会自动保存到数据库，并刷新当前持仓快照。</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="openAddDialog">新增持仓</el-button>
          <el-button :loading="actionLoading || loading" @click="refreshHoldings">刷新持仓</el-button>
          <el-button type="success" :loading="actionLoading" @click="runAnalysis">运行持仓分析</el-button>
        </div>
      </div>

      <el-form class="action-form" label-width="92px">
        <el-form-item label="快照日期">
          <el-date-picker v-model="positionDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="运行 ID">
          <el-input-number v-model="runId" :min="1" clearable />
          <span class="form-note">留空时自动使用最近一次目标组合；只有需要指定某次策略运行时才填写。</span>
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
        title="新增、编辑或补仓确认后会自动保存；不在 ETF 池里的代码会自动登记，缺行情时会自动尝试同步。"
      />

      <el-table :data="visibleRows" height="380" empty-text="暂无持仓，点击“新增持仓”开始录入">
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column label="名称" min-width="130">
          <template #default="{ row }">{{ row.position_name || '待补全' }}</template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }"><el-tag size="small">{{ assetTypeText(row.asset_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="持仓数量" width="120">
          <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
        </el-table-column>
        <el-table-column label="成本价" width="110">
          <template #default="{ row }">{{ formatPrice(row.cost_price) }}</template>
        </el-table-column>
        <el-table-column label="现价" width="110">
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
        <el-table-column label="状态" min-width="150">
          <template #default="{ row }">
            <el-tag v-if="row.resolved" size="small" type="success">已补全</el-tag>
            <span v-else class="muted">{{ row.resolve_message || '等待补全' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row, $index }">
            <el-button text type="primary" @click="openEditDialog(row, $index)">编辑</el-button>
            <el-button text type="success" @click="openTopupDialog(row, $index)">补仓</el-button>
            <el-button text type="danger" @click="removeRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog v-model="positionDialog.visible" :title="dialogTitle" width="520px">
        <el-form label-width="104px">
          <el-form-item label="证券代码" required>
            <el-input
              v-model="positionForm.symbol"
              :disabled="positionDialog.mode === 'topup'"
              placeholder="例如 513050"
              @change="resolveDialogSymbol"
            />
          </el-form-item>

          <template v-if="positionDialog.mode === 'topup'">
            <el-form-item label="当前数量">
              <span>{{ formatQuantity(activeRow?.quantity || 0) }}</span>
            </el-form-item>
            <el-form-item label="当前成本价">
              <span>{{ formatPrice(activeRow?.cost_price || 0) }}</span>
            </el-form-item>
            <el-form-item label="追加数量" required>
              <el-input-number v-model="positionForm.topup_quantity" :min="0" :step="100" />
            </el-form-item>
            <el-form-item label="补仓成交价" required>
              <el-input-number v-model="positionForm.topup_price" :min="0" :precision="3" :step="0.001" />
            </el-form-item>
            <el-form-item label="补仓后">
              <span>数量 {{ formatQuantity(topupPreview.quantity) }}，成本价 {{ formatPrice(topupPreview.costPrice) }}</span>
            </el-form-item>
          </template>

          <template v-else>
            <el-form-item label="持仓数量" required>
              <el-input-number v-model="positionForm.quantity" :min="0" :step="100" />
            </el-form-item>
            <el-form-item label="成本价" required>
              <el-input-number v-model="positionForm.cost_price" :min="0" :precision="3" :step="0.001" />
            </el-form-item>
            <el-form-item v-if="!positionForm.current_price" label="临时现价">
              <el-input-number v-model="positionForm.current_price" :min="0" :precision="3" :step="0.001" />
              <span class="form-note">自动同步失败时可临时填写，后续同步行情后会自动覆盖。</span>
            </el-form-item>
          </template>

          <el-form-item label="系统补全">
            <div class="dialog-resolve">
              <span>{{ positionForm.position_name || '待补全名称' }}</span>
              <el-tag size="small">{{ assetTypeText(positionForm.asset_type) }}</el-tag>
              <span>现价 {{ positionForm.current_price ? formatPrice(positionForm.current_price) : '-' }}</span>
            </div>
          </el-form-item>
          <el-form-item v-if="positionForm.resolve_message" label="提示">
            <span class="muted">{{ positionForm.resolve_message }}</span>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="positionDialog.visible = false">取消</el-button>
          <el-button :loading="actionLoading" @click="resolveDialogSymbol">自动补全/同步</el-button>
          <el-button type="primary" :loading="actionLoading" @click="confirmPositionDialog">确定并保存</el-button>
        </template>
      </el-dialog>
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
import { computed, onMounted, reactive, ref } from 'vue'
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

type DialogMode = 'add' | 'edit' | 'topup'

const loading = ref(false)
const actionLoading = ref(false)
const positionDate = ref(new Date().toISOString().slice(0, 10))
const runId = ref<number | undefined>()
const positions = ref<PortfolioPosition[]>([])
const analysis = ref<HoldingAnalysis[]>([])
const draftRows = ref<DraftPosition[]>([])
const positionDialog = reactive({ visible: false, mode: 'add' as DialogMode, index: -1 })
const positionForm = reactive({
  symbol: '',
  position_name: '',
  asset_type: 'etf' as DraftPosition['asset_type'],
  quantity: 0,
  current_price: 0,
  cost_price: 0,
  price_date: '',
  resolved: false,
  resolve_message: '',
  topup_quantity: 0,
  topup_price: 0,
})

const visibleRows = computed(() => draftRows.value.filter((row) => row.symbol.trim()))
const activeRow = computed(() => (positionDialog.index >= 0 ? draftRows.value[positionDialog.index] : null))
const dialogTitle = computed(() => {
  if (positionDialog.mode === 'edit') return '编辑持仓'
  if (positionDialog.mode === 'topup') return '补仓'
  return '新增持仓'
})
const topupPreview = computed(() => {
  const row = activeRow.value
  const currentQuantity = Number(row?.quantity || 0)
  const currentCost = Number(row?.cost_price || 0)
  const addQuantity = Number(positionForm.topup_quantity || 0)
  const addPrice = Number(positionForm.topup_price || 0)
  const quantity = currentQuantity + addQuantity
  const costBasis = currentQuantity * currentCost + addQuantity * addPrice
  return {
    quantity,
    costPrice: quantity > 0 ? costBasis / quantity : 0,
  }
})
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
    draftRows.value = positions.value.map(positionToDraft)
  } finally {
    loading.value = false
  }
}

function positionToDraft(item: PortfolioPosition): DraftPosition {
  return {
    symbol: item.symbol,
    position_name: item.position_name || '',
    asset_type: normalizeAssetType(item.asset_type),
    quantity: Number(item.quantity || 0),
    current_price: Number(item.current_price || 0),
    cost_price: Number(item.cost_price || 0),
    price_date: item.position_date,
    resolved: Boolean(item.position_name && item.current_price),
    resolve_message: '',
  }
}

function resetPositionForm(row?: DraftPosition) {
  positionForm.symbol = row?.symbol || ''
  positionForm.position_name = row?.position_name || ''
  positionForm.asset_type = normalizeAssetType(row?.asset_type || 'etf')
  positionForm.quantity = Number(row?.quantity || 0)
  positionForm.current_price = Number(row?.current_price || 0)
  positionForm.cost_price = Number(row?.cost_price || 0)
  positionForm.price_date = row?.price_date || ''
  positionForm.resolved = Boolean(row?.resolved)
  positionForm.resolve_message = row?.resolve_message || ''
  positionForm.topup_quantity = 0
  positionForm.topup_price = Number(row?.current_price || row?.cost_price || 0)
}

function openAddDialog() {
  positionDialog.mode = 'add'
  positionDialog.index = -1
  resetPositionForm()
  positionDialog.visible = true
}

function openEditDialog(row: DraftPosition, index: number) {
  positionDialog.mode = 'edit'
  positionDialog.index = index
  resetPositionForm(row)
  positionDialog.visible = true
}

function openTopupDialog(row: DraftPosition, index: number) {
  positionDialog.mode = 'topup'
  positionDialog.index = index
  resetPositionForm(row)
  positionDialog.visible = true
}

function removeRow(index: number) {
  draftRows.value.splice(index, 1)
}

async function resolveRows() {
  const symbols = draftRows.value.map((row) => row.symbol.trim()).filter(Boolean)
  if (!symbols.length) {
    ElMessage.warning('请先新增持仓')
    return
  }
  actionLoading.value = true
  try {
    const details = await resolvePositionSymbols(symbols, { auto_sync: true, source: 'akshare' })
    const detailMap = new Map(details.map((item) => [item.symbol, item]))
    draftRows.value = draftRows.value.map((row) => applyResolveDetail(row, detailMap.get(row.symbol.trim())))
    const unresolvedCount = details.filter((item) => !item.resolved).length
    if (unresolvedCount) {
      ElMessage.warning(`${unresolvedCount} 个代码未完全补全，可临时填写现价后保存，后续再同步行情`)
    } else {
      ElMessage.success('名称、类型和现价已刷新')
    }
  } catch (error) {
    ElMessage.error(errorMessage(error, '刷新失败'))
  } finally {
    actionLoading.value = false
  }
}

async function refreshHoldings() {
  if (!draftRows.value.length) {
    await refresh()
    return
  }
  await resolveRows()
  await refresh()
}

async function resolveDialogSymbol() {
  const symbol = positionForm.symbol.trim()
  if (!symbol) {
    ElMessage.warning('请先填写代码')
    return
  }
  actionLoading.value = true
  try {
    const [detail] = await resolvePositionSymbols([symbol], { auto_sync: true, source: 'akshare' })
    if (!detail) return
    positionForm.symbol = detail.symbol
    positionForm.position_name = detail.position_name || positionForm.position_name
    positionForm.asset_type = normalizeAssetType(detail.asset_type)
    positionForm.current_price = Number(detail.current_price || 0)
    positionForm.price_date = detail.price_date || ''
    positionForm.resolved = detail.resolved
    positionForm.resolve_message = detail.message || ''
    if (!detail.resolved) {
      ElMessage.warning(detail.message || '该代码未完全补全，可临时填写现价后保存')
    }
  } catch (error) {
    ElMessage.error(errorMessage(error, '补全失败'))
  } finally {
    actionLoading.value = false
  }
}

async function confirmPositionDialog() {
  const symbol = positionForm.symbol.trim()
  if (!symbol) {
    ElMessage.warning('请填写代码')
    return
  }

  if (positionDialog.mode === 'topup') {
    if (!activeRow.value) return
    if (Number(positionForm.topup_quantity || 0) <= 0 || Number(positionForm.topup_price || 0) <= 0) {
      ElMessage.warning('请填写有效的追加数量和补仓成交价')
      return
    }
    draftRows.value[positionDialog.index] = {
      ...activeRow.value,
      quantity: roundNumber(topupPreview.value.quantity, 4),
      cost_price: roundNumber(topupPreview.value.costPrice, 6),
    }
    positionDialog.visible = false
    await persistSnapshot('补仓信息已自动保存')
    return
  }

  if (Number(positionForm.quantity || 0) <= 0 || Number(positionForm.cost_price || 0) <= 0) {
    ElMessage.warning('请填写有效的持仓数量和成本价')
    return
  }

  const duplicateIndex = draftRows.value.findIndex((row, index) => row.symbol === symbol && index !== positionDialog.index)
  if (duplicateIndex >= 0) {
    ElMessage.warning('该代码已存在，请使用编辑或补仓')
    return
  }

  const row: DraftPosition = {
    symbol,
    position_name: positionForm.position_name,
    asset_type: positionForm.asset_type,
    quantity: Number(positionForm.quantity || 0),
    current_price: Number(positionForm.current_price || 0),
    cost_price: Number(positionForm.cost_price || 0),
    price_date: positionForm.price_date,
    resolved: positionForm.resolved,
    resolve_message: positionForm.resolve_message,
  }
  if (positionDialog.mode === 'edit' && positionDialog.index >= 0) {
    draftRows.value[positionDialog.index] = row
  } else {
    draftRows.value.push(row)
  }
  positionDialog.visible = false
  await persistSnapshot(positionDialog.mode === 'edit' ? '持仓编辑已自动保存' : '新增持仓已自动保存')
}

async function persistSnapshot(successMessage: string) {
  actionLoading.value = true
  try {
    const rows = draftRows.value
      .filter((row) => row.symbol.trim() && Number(row.quantity || 0) > 0)
      .map((row) => ({
        symbol: row.symbol.trim(),
        quantity: row.quantity,
        current_price: row.current_price || undefined,
        cost_price: row.cost_price,
      }))
    if (!rows.length) {
      ElMessage.warning('请至少新增一条有效持仓')
      return
    }
    positions.value = await savePositionSnapshot({ position_date: positionDate.value, positions: rows })
    ElMessage.success(successMessage)
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
    analysis.value = await analyzeHoldings({ run_id: runId.value || undefined, analysis_date: positionDate.value })
    ElMessage.success('持仓分析完成')
  } catch (error) {
    ElMessage.error(errorMessage(error, '分析失败'))
  } finally {
    actionLoading.value = false
  }
}

function applyResolveDetail(row: DraftPosition, detail: Awaited<ReturnType<typeof resolvePositionSymbols>>[number] | undefined) {
  if (!detail) return row
  return {
    ...row,
    symbol: detail.symbol,
    position_name: detail.position_name || row.position_name,
    asset_type: normalizeAssetType(detail.asset_type),
    current_price: Number(detail.current_price || 0),
    price_date: detail.price_date || '',
    resolved: detail.resolved,
    resolve_message: detail.message || '',
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
  return roundNumber(value, 2)
}

function roundNumber(value: number, precision: number) {
  const factor = 10 ** precision
  return Math.round(Number(value || 0) * factor) / factor
}

function formatMoney(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPrice(value: number) {
  return Number(value || 0).toFixed(3)
}

function formatQuantity(value: number) {
  return Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
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
