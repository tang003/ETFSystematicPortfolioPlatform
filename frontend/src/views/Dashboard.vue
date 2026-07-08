<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-3"><div class="metric">Enabled ETFs<strong>{{ assets.length }}</strong></div></section>
    <section class="panel span-3"><div class="metric">Data Logs<strong>{{ quality?.total_logs ?? 0 }}</strong></div></section>
    <section class="panel span-3"><div class="metric">Factor Rows<strong>{{ factors.length }}</strong></div></section>
    <section class="panel span-3"><div class="metric">Target Positions<strong>{{ targets.length }}</strong></div></section>
    <section class="panel span-6">
      <h2>Alpha Ranking</h2>
      <div ref="rankingChart" class="chart"></div>
    </section>
    <section class="panel span-6">
      <h2>Target Allocation</h2>
      <div ref="portfolioChart" class="chart"></div>
    </section>
    <section class="panel span-12">
      <h2>Recent Orders</h2>
      <el-table :data="orders" height="260">
        <el-table-column prop="symbol" label="Symbol" width="120" />
        <el-table-column prop="action" label="Action" width="120" />
        <el-table-column prop="target_weight" label="Target" width="120" />
        <el-table-column prop="estimated_amount" label="Amount" />
        <el-table-column prop="status" label="Status" width="120" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchAssets, fetchDataQualityStatus, fetchFactorRanking, fetchRebalanceOrders, fetchTargetPortfolio, type Asset, type DataQualityStatus, type Factor, type RebalanceOrder, type TargetPortfolio } from '../api/client'

const loading = ref(true)
const assets = ref<Asset[]>([])
const quality = ref<DataQualityStatus>()
const factors = ref<Factor[]>([])
const targets = ref<TargetPortfolio[]>([])
const orders = ref<RebalanceOrder[]>([])
const rankingChart = ref<HTMLElement>()
const portfolioChart = ref<HTMLElement>()

onMounted(async () => {
  try {
    const [assetData, qualityData, factorData, targetData, orderData] = await Promise.all([
      fetchAssets(),
      fetchDataQualityStatus(),
      fetchFactorRanking(),
      fetchTargetPortfolio(),
      fetchRebalanceOrders(),
    ])
    assets.value = assetData.filter((item) => item.enabled)
    quality.value = qualityData
    factors.value = factorData
    targets.value = targetData
    orders.value = orderData
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
})

function renderCharts() {
  if (rankingChart.value) {
    echarts.init(rankingChart.value).setOption({
      tooltip: {},
      xAxis: { type: 'category', data: factors.value.map((item) => item.symbol) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: factors.value.map((item) => Number(item.alpha_score ?? 0)), itemStyle: { color: '#2563eb' } }],
    })
  }
  if (portfolioChart.value) {
    echarts.init(portfolioChart.value).setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: ['45%', '70%'], data: targets.value.map((item) => ({ name: item.symbol, value: Number(item.final_target_weight ?? 0) })) }],
    })
  }
}
</script>

