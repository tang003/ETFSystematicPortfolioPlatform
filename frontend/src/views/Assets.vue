<template>
  <section class="panel">
    <h2>ETF 池</h2>
    <el-table :data="assets" v-loading="loading" height="680">
      <el-table-column prop="symbol" label="代码" width="120" />
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="exchange" label="交易所" width="110" />
      <el-table-column prop="asset_class" label="资产类别" width="120" />
      <el-table-column prop="asset_region" label="区域" width="120" />
      <el-table-column prop="risk_level" label="风险等级" width="100" />
      <el-table-column label="跨境" width="100">
        <template #default="{ row }"><el-tag :type="row.is_cross_border ? 'warning' : 'info'">{{ row.is_cross_border ? '是' : '否' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="启用" width="100">
        <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template>
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
