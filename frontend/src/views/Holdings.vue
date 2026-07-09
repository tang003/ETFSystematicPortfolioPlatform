<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>录入当前持仓</h2>
        <div>
          <el-button @click="addRow">新增一行</el-button>
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
          <span class="form-note">用于和某次目标组合对比。</span>
        </el-form-item>
      </el-form>
      <el-table :data="draftRows" height="260">
        <el-table-column label="ETF 代码" width="150">
          <template #default="{ row }"><el-input v-model="row.symbol" placeholder="510300" /></template>
        </el-table-column>
        <el-table-column label="份额" width="160">
          <template #default="{ row }"><el-input-number v-model="row.quantity" :min="0" /></template>
        </el-table-column>
        <el-table-column label="当前市值" width="180">
          <template #default="{ row }"><el-input-number v-model="row.market_value" :min="0" :step="1000" /></template>
        </el-table-column>
        <el-table-column label="持仓成本" width="180">
          <template #default="{ row }"><el-input-number v-model="row.cost_basis" :min="0" :step="1000" /></template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ $index }"><el-button text type="danger" @click="removeRow($index)">删除</el-button></template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-5">
      <h2>当前持仓权重</h2>
      <el-table :data="positions" height="360">
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="market_value" label="市值" width="140" />
        <el-table-column prop="weight" label="当前权重" width="120" />
        <el-table-column prop="cost_basis" label="成本" min-width="120" />
      </el-table>
    </section>

    <section class="panel span-7">
      <h2>持仓分析结果</h2>
      <el-table :data="analysis" height="360">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column label="建议" width="120">
          <template #default="{ row }"><el-tag :type="tagType(row.action_suggestion)">{{ actionText(row.action_suggestion) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="current_weight" label="当前权重" width="120" />
        <el-table-column prop="target_weight" label="目标权重" width="120" />
        <el-table-column prop="weight_diff" label="差异" width="110" />
        <el-table-column prop="alpha_score" label="Alpha" width="100" />
        <el-table-column prop="reason" label="原因" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyzeHoldings, fetchHoldingAnalysis, fetchPositions, savePositionSnapshot, type HoldingAnalysis, type PortfolioPosition } from '../api/client'

interface DraftPosition {
  symbol: string
  quantity: number
  market_value: number
  cost_basis: number
}

const loading = ref(false)
const actionLoading = ref(false)
const positionDate = ref(new Date().toISOString().slice(0, 10))
const runId = ref(1)
const positions = ref<PortfolioPosition[]>([])
const analysis = ref<HoldingAnalysis[]>([])
const draftRows = ref<DraftPosition[]>([
  { symbol: '510300', quantity: 0, market_value: 30000, cost_basis: 30000 },
  { symbol: '511880', quantity: 0, market_value: 20000, cost_basis: 20000 },
])

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    ;[positions.value, analysis.value] = await Promise.all([fetchPositions(), fetchHoldingAnalysis()])
  } finally {
    loading.value = false
  }
}

function addRow() {
  draftRows.value.push({ symbol: '', quantity: 0, market_value: 0, cost_basis: 0 })
}

function removeRow(index: number) {
  draftRows.value.splice(index, 1)
}

async function saveSnapshot() {
  actionLoading.value = true
  try {
    const rows = draftRows.value
      .filter((row) => row.symbol.trim() && row.market_value > 0)
      .map((row) => ({ symbol: row.symbol.trim(), quantity: row.quantity, market_value: row.market_value, cost_basis: row.cost_basis }))
    if (!rows.length) {
      ElMessage.warning('请至少填写一条有效持仓')
      return
    }
    positions.value = await savePositionSnapshot({ position_date: positionDate.value, positions: rows })
    ElMessage.success('持仓快照已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
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
    ElMessage.error(error instanceof Error ? error.message : '分析失败')
  } finally {
    actionLoading.value = false
  }
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
</script>
