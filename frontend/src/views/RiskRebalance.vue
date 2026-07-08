<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-6">
      <h2>Risk Results</h2>
      <el-table :data="riskResults" height="520">
        <el-table-column prop="run_id" label="Run" width="90" />
        <el-table-column prop="rule_code" label="Rule" width="180" />
        <el-table-column prop="status" label="Status" width="110" />
        <el-table-column prop="before_value" label="Before" width="120" />
        <el-table-column prop="after_value" label="After" width="120" />
        <el-table-column prop="message" label="Message" min-width="220" />
      </el-table>
    </section>
    <section class="panel span-6">
      <h2>Rebalance Orders</h2>
      <el-table :data="orders" height="520">
        <el-table-column prop="symbol" label="Symbol" width="110" />
        <el-table-column prop="action" label="Action" width="110" />
        <el-table-column prop="target_weight" label="Target" width="120" />
        <el-table-column prop="estimated_amount" label="Amount" width="140" />
        <el-table-column prop="status" label="Status" width="120" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchRebalanceOrders, fetchRiskResults, type RebalanceOrder, type RiskResult } from '../api/client'

const riskResults = ref<RiskResult[]>([])
const orders = ref<RebalanceOrder[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    ;[riskResults.value, orders.value] = await Promise.all([fetchRiskResults(), fetchRebalanceOrders()])
  } finally {
    loading.value = false
  }
})
</script>

