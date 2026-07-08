<template>
  <section class="panel">
    <h2>ETF Pool</h2>
    <el-table :data="assets" v-loading="loading" height="680">
      <el-table-column prop="symbol" label="Symbol" width="120" />
      <el-table-column prop="name" label="Name" min-width="180" />
      <el-table-column prop="exchange" label="Exchange" width="110" />
      <el-table-column prop="asset_class" label="Class" width="120" />
      <el-table-column prop="asset_region" label="Region" width="120" />
      <el-table-column prop="risk_level" label="Risk" width="90" />
      <el-table-column label="Cross Border" width="140">
        <template #default="{ row }"><el-tag :type="row.is_cross_border ? 'warning' : 'info'">{{ row.is_cross_border ? 'Yes' : 'No' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="Enabled" width="110">
        <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Enabled' : 'Disabled' }}</el-tag></template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAssets, type Asset } from '../api/client'

const assets = ref<Asset[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    assets.value = await fetchAssets()
  } finally {
    loading.value = false
  }
})
</script>

