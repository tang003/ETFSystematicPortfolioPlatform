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
        <el-table-column prop="trade_date" label="日期" width="130" />
        <el-table-column prop="alpha_score" label="Alpha" width="120" sortable />
        <el-table-column prop="trend_score" label="趋势" width="120" />
        <el-table-column prop="momentum_score" label="动量" width="130" />
        <el-table-column prop="volatility_score" label="波动率" width="130" />
        <el-table-column prop="drawdown_score" label="回撤" width="130" />
        <el-table-column prop="liquidity_score" label="流动性" width="130" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { calculateFactors, fetchFactorRanking, type Factor } from '../api/client'

const factors = ref<Factor[]>([])
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
  } finally {
    loading.value = false
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
</script>
