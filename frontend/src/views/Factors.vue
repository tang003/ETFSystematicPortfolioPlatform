<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <h2>Factor Ranking</h2>
      <el-table :data="factors" height="640">
        <el-table-column prop="symbol" label="Symbol" width="120" />
        <el-table-column prop="trade_date" label="Date" width="130" />
        <el-table-column prop="alpha_score" label="Alpha" width="120" sortable />
        <el-table-column prop="trend_score" label="Trend" width="120" />
        <el-table-column prop="momentum_score" label="Momentum" width="130" />
        <el-table-column prop="volatility_score" label="Volatility" width="130" />
        <el-table-column prop="drawdown_score" label="Drawdown" width="130" />
        <el-table-column prop="liquidity_score" label="Liquidity" width="130" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchFactorRanking, type Factor } from '../api/client'

const factors = ref<Factor[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    factors.value = await fetchFactorRanking()
  } finally {
    loading.value = false
  }
})
</script>

