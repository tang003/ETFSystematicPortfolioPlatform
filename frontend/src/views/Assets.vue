<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-4">
      <div class="panel-header">
        <h2>ETF 池管理</h2>
        <el-button type="primary" :loading="actionLoading" @click="importPresetAssets">导入扩展示例池</el-button>
      </div>
      <el-form label-width="96px">
        <el-form-item label="批量导入">
          <el-input
            v-model="importText"
            type="textarea"
            :rows="14"
            placeholder="每行一个 ETF，格式：代码,名称,交易所,资产类别,区域,风险等级,说明"
          />
        </el-form-item>
        <el-form-item label="格式示例">
          <div class="source-hint">
            <strong>导入格式</strong>
            <p>510050,上证50ETF,SH,equity,CN,4,A股核心蓝筹 ETF</p>
            <p>513100,纳指ETF,SH,equity,US,5,跨境美国科技成长 ETF</p>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="actionLoading" @click="submitImport">批量导入到 ETF 池</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <h2>ETF 主数据</h2>
        <el-tag type="success">共 {{ assets.length }} 只</el-tag>
      </div>
      <el-table :data="assets" height="680">
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { batchUpsertAssets, fetchAssets, type Asset, type AssetUpsertItem } from '../api/client'

const assets = ref<Asset[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const importText = ref('')

const presetAssets: AssetUpsertItem[] = [
  { symbol: '510050', name: '上证50ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: 'A股核心蓝筹 ETF' },
  { symbol: '159928', name: '消费ETF', exchange: 'SZ', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: 'A股消费行业 ETF' },
  { symbol: '510880', name: '红利ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 3, description: '高股息红利 ETF' },
  { symbol: '512170', name: '医疗ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股医疗行业 ETF' },
  { symbol: '512660', name: '军工ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股军工行业 ETF' },
  { symbol: '512880', name: '证券ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股券商行业 ETF' },
  { symbol: '513050', name: '中概互联网ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN_HK_US', risk_level: 5, is_cross_border: true, description: '中概互联网主题 ETF' },
  { symbol: '159920', name: '恒生ETF', exchange: 'SZ', asset_class: 'equity', asset_region: 'HK', risk_level: 4, is_cross_border: true, description: '港股宽基 ETF' },
]

onMounted(async () => {
  await refresh()
})

async function refresh() {
  try {
    assets.value = await fetchAssets()
  } finally {
    loading.value = false
  }
}

async function importPresetAssets() {
  actionLoading.value = true
  try {
    const result = await batchUpsertAssets({ items: presetAssets })
    ElMessage.success(`已导入 ${result.inserted_or_updated} 条扩展示例 ETF`)
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    actionLoading.value = false
  }
}

async function submitImport() {
  const items = parseImportText(importText.value)
  if (!items.length) {
    ElMessage.warning('请先填写至少一行 ETF 主数据')
    return
  }
  actionLoading.value = true
  try {
    const result = await batchUpsertAssets({ items })
    ElMessage.success(`已写入 ${result.inserted_or_updated} 条 ETF 主数据`)
    importText.value = ''
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    actionLoading.value = false
  }
}

function parseImportText(value: string): AssetUpsertItem[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [symbol, name, exchange, assetClass, assetRegion, riskLevel, description] = line.split(/[,\t，]/).map((item) => item.trim())
      return {
        symbol,
        name,
        exchange: exchange || null,
        asset_class: assetClass || 'equity',
        asset_region: assetRegion || 'CN',
        risk_level: Number(riskLevel || 3),
        description: description || null,
        currency: 'CNY',
        is_cross_border: ['US', 'HK', 'GLOBAL', 'CN_HK_US'].includes(assetRegion || ''),
        enabled: true,
      }
    })
    .filter((item) => item.symbol && item.name)
}
</script>
