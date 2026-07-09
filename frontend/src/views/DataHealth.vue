<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>数据更新与检查</h2>
        <el-button type="primary" :loading="actionLoading" @click="runFullDataFlow">一键更新并检查</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbolsText" placeholder="留空代表全部启用 ETF，多个代码用逗号分隔" />
        </el-form-item>
        <el-form-item label="同步数量">
          <el-input-number v-model="maxSymbols" :min="1" :max="50" />
          <span class="form-note">避免一次请求过久，默认先同步 10 只。</span>
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
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { checkDataQuality, fetchDataQualityLogs, fetchDataQualityStatus, syncCalendar, syncMarket, type DataQualityLog, type DataQualityStatus } from '../api/client'

const status = ref<DataQualityStatus>()
const logs = ref<DataQualityLog[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const today = new Date().toISOString().slice(0, 10)
const lastMonth = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([lastMonth, today])
const symbolsText = ref('')
const maxSymbols = ref(10)

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    ;[status.value, logs.value] = await Promise.all([fetchDataQualityStatus(), fetchDataQualityLogs()])
  } finally {
    loading.value = false
  }
}

async function runCalendarSync() {
  await withAction('交易日历同步完成', () => syncCalendar({ start_date: dateRange.value[0], end_date: dateRange.value[1], market: 'CN' }))
}

async function runMarketSync() {
  await withAction('行情同步完成', () => syncMarket({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols: splitSymbols(), max_symbols: maxSymbols.value, clean_after_sync: true }))
}

async function runQualityCheck() {
  const symbols = splitSymbols()
  if (!symbols.length) {
    ElMessage.warning('缺失数据检查需要填写至少一个 ETF 代码')
    return
  }
  await withAction('缺失数据检查完成', () => checkDataQuality({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols }))
}

async function runFullDataFlow() {
  actionLoading.value = true
  try {
    await syncCalendar({ start_date: dateRange.value[0], end_date: dateRange.value[1], market: 'CN' })
    await syncMarket({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols: splitSymbols(), max_symbols: maxSymbols.value, clean_after_sync: true })
    const symbols = splitSymbols()
    if (symbols.length) await checkDataQuality({ start_date: dateRange.value[0], end_date: dateRange.value[1], symbols })
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
</script>
