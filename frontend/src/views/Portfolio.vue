<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-5">
      <h2>Allocation</h2>
      <div ref="chartRef" class="chart"></div>
    </section>
    <section class="panel span-7">
      <h2>Target Portfolio</h2>
      <el-table :data="targets" height="360">
        <el-table-column prop="symbol" label="Symbol" width="110" />
        <el-table-column prop="asset_class" label="Class" width="120" />
        <el-table-column prop="raw_target_weight" label="Raw" width="120" />
        <el-table-column prop="final_target_weight" label="Final" width="120" />
        <el-table-column prop="reason" label="Reason" min-width="240" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchTargetPortfolio, type TargetPortfolio } from '../api/client'

const targets = ref<TargetPortfolio[]>([])
const loading = ref(true)
const chartRef = ref<HTMLElement>()

onMounted(async () => {
  try {
    targets.value = await fetchTargetPortfolio()
    await nextTick()
    if (chartRef.value) {
      echarts.init(chartRef.value).setOption({
        tooltip: { trigger: 'item' },
        series: [{ type: 'pie', radius: '70%', data: targets.value.map((item) => ({ name: item.symbol, value: Number(item.final_target_weight ?? 0) })) }],
      })
    }
  } finally {
    loading.value = false
  }
})
</script>

