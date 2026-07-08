<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-3"><div class="metric">Status<strong>{{ status?.status ?? '-' }}</strong></div></section>
    <section class="panel span-3"><div class="metric">Errors<strong>{{ status?.error_logs ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">Warnings<strong>{{ status?.warning_logs ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">Total Logs<strong>{{ status?.total_logs ?? 0 }}</strong></div></section>
    <section class="panel span-12">
      <h2>Quality Logs</h2>
      <el-table :data="logs" height="560">
        <el-table-column prop="created_at" label="Created" width="190" />
        <el-table-column prop="symbol" label="Symbol" width="110" />
        <el-table-column prop="trade_date" label="Date" width="130" />
        <el-table-column prop="check_type" label="Check" width="180" />
        <el-table-column prop="severity" label="Severity" width="120" />
        <el-table-column prop="message" label="Message" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchDataQualityLogs, fetchDataQualityStatus, type DataQualityLog, type DataQualityStatus } from '../api/client'

const status = ref<DataQualityStatus>()
const logs = ref<DataQualityLog[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    ;[status.value, logs.value] = await Promise.all([fetchDataQualityStatus(), fetchDataQualityLogs()])
  } finally {
    loading.value = false
  }
})
</script>

