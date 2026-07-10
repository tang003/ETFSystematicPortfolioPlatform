<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>ETF 池管理</h2>
          <p class="section-note">维护策略研究对象，只保留 ETF、场内基金、货币/债券/商品 ETF 等可配置资产。</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" :loading="actionLoading" @click="importPresetAssets">导入精选 ETF 示例池</el-button>
          <el-button @click="copyEnabledSymbols">复制已启用代码</el-button>
        </div>
      </div>

      <div class="summary-grid asset-summary">
        <div class="metric">ETF 总数<strong>{{ assets.length }}</strong></div>
        <div class="metric">启用研究<strong>{{ enabledAssets.length }}</strong></div>
        <div class="metric">跨境 ETF<strong>{{ crossBorderCount }}</strong></div>
        <div class="metric">高风险主题<strong>{{ highRiskCount }}</strong></div>
      </div>

      <div class="quick-filter-bar">
        <el-button :type="assetClassFilter === 'all' ? 'primary' : 'default'" @click="assetClassFilter = 'all'">全部</el-button>
        <el-button
          v-for="item in classQuickFilters"
          :key="item.value"
          :type="assetClassFilter === item.value ? 'primary' : 'default'"
          @click="assetClassFilter = item.value"
        >
          {{ item.label }}
        </el-button>
      </div>
    </section>

    <section class="panel span-4">
      <div class="panel-header">
        <h2>批量导入</h2>
      </div>
      <el-form label-width="96px">
        <el-form-item label="导入内容">
          <el-input
            v-model="importText"
            type="textarea"
            :rows="13"
            placeholder="每行一个 ETF，格式：代码,名称,交易所,资产类别,区域,风险等级,说明"
          />
        </el-form-item>
        <el-form-item label="格式示例">
          <div class="source-hint">
            <strong>导入格式</strong>
            <p>510300,沪深300ETF,SH,equity,CN,4,A股核心宽基 ETF</p>
            <p>518880,黄金ETF,SH,gold,CN,3,黄金商品 ETF</p>
            <p>513100,纳指ETF,SH,qdii,US,5,跨境美国科技成长 ETF</p>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="actionLoading" @click="submitImport">批量导入到 ETF 池</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <div>
          <h2>ETF 主数据</h2>
          <p class="section-note">筛选后 {{ filteredAssets.length }} 只，启用后会进入行情同步、因子计算、策略和回测流程。</p>
        </div>
        <div class="task-tags">
          <el-tag type="success">启用 {{ enabledAssets.length }}</el-tag>
          <el-tag type="info">筛选 {{ filteredAssets.length }}</el-tag>
        </div>
      </div>
      <el-form class="action-form assets-filter-form" label-width="84px">
        <el-form-item label="搜索">
          <el-input v-model="keyword" clearable placeholder="代码 / 名称 / 说明" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-select v-model="enabledFilter">
            <el-option label="全部" value="all" />
            <el-option label="仅启用" value="enabled" />
            <el-option label="仅停用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="资产类别">
          <el-select v-model="assetClassFilter">
            <el-option label="全部" value="all" />
            <el-option v-for="item in assetClassOptions" :key="item" :label="assetClassText(item)" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域">
          <el-select v-model="assetRegionFilter">
            <el-option label="全部" value="all" />
            <el-option v-for="item in assetRegionOptions" :key="item" :label="regionText(item)" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险上限">
          <el-slider v-model="riskLevelMax" :min="1" :max="5" show-stops />
        </el-form-item>
        <el-form-item label="跨境">
          <el-select v-model="crossBorderFilter">
            <el-option label="全部" value="all" />
            <el-option label="仅跨境" value="yes" />
            <el-option label="仅境内" value="no" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="filteredAssets" height="620" empty-text="暂无 ETF，先导入示例池或批量导入">
        <el-table-column prop="symbol" label="代码" width="110" fixed />
        <el-table-column prop="name" label="名称" min-width="170" />
        <el-table-column label="类别" width="110">
          <template #default="{ row }"><el-tag size="small">{{ assetClassText(row.asset_class) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="区域" width="120">
          <template #default="{ row }">{{ regionText(row.asset_region) }}</template>
        </el-table-column>
        <el-table-column label="风险" width="120">
          <template #default="{ row }">
            <el-tag :type="riskTagType(row.risk_level)" size="small">{{ riskText(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="跨境" width="90">
          <template #default="{ row }"><el-tag :type="row.is_cross_border ? 'warning' : 'info'" size="small">{{ row.is_cross_border ? '是' : '否' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="exchange" label="交易所" width="90" />
        <el-table-column label="启用研究" width="120">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" :loading="togglingSymbol === row.symbol" @change="(value: string | number | boolean) => toggleAsset(row.symbol, value)" />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { batchUpsertAssets, fetchAssets, updateAsset, type Asset, type AssetUpsertItem } from '../api/client'

const assets = ref<Asset[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const importText = ref('')
const keyword = ref('')
const enabledFilter = ref<'all' | 'enabled' | 'disabled'>('all')
const assetClassFilter = ref('all')
const assetRegionFilter = ref('all')
const crossBorderFilter = ref<'all' | 'yes' | 'no'>('all')
const riskLevelMax = ref(5)
const togglingSymbol = ref('')

const classQuickFilters = [
  { label: '宽基权益', value: 'equity' },
  { label: '债券', value: 'bond' },
  { label: '黄金/商品', value: 'gold' },
  { label: '货币现金', value: 'cash' },
  { label: '跨境 QDII', value: 'qdii' },
]

const presetAssets: AssetUpsertItem[] = [
  { symbol: '510050', name: '上证50ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: 'A股核心蓝筹 ETF' },
  { symbol: '510300', name: '沪深300ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: 'A股核心宽基 ETF' },
  { symbol: '510500', name: '中证500ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: 'A股中盘宽基 ETF' },
  { symbol: '512100', name: '中证1000ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股小盘宽基 ETF' },
  { symbol: '159915', name: '创业板ETF', exchange: 'SZ', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '创业板成长 ETF' },
  { symbol: '588000', name: '科创50ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '科创板核心 ETF' },
  { symbol: '510880', name: '红利ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 3, description: '高股息红利 ETF' },
  { symbol: '512800', name: '银行ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: '银行行业 ETF' },
  { symbol: '512000', name: '券商ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '券商行业 ETF' },
  { symbol: '159928', name: '消费ETF', exchange: 'SZ', asset_class: 'equity', asset_region: 'CN', risk_level: 4, description: 'A股消费行业 ETF' },
  { symbol: '512010', name: '医药ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股医药行业 ETF' },
  { symbol: '512170', name: '医疗ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股医疗行业 ETF' },
  { symbol: '512760', name: '芯片ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '半导体芯片主题 ETF' },
  { symbol: '512480', name: '半导体ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '半导体主题 ETF' },
  { symbol: '515790', name: '光伏ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '新能源光伏主题 ETF' },
  { symbol: '516160', name: '新能源ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: '新能源产业 ETF' },
  { symbol: '512660', name: '军工ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, description: 'A股军工行业 ETF' },
  { symbol: '159920', name: '恒生ETF', exchange: 'SZ', asset_class: 'qdii', asset_region: 'HK', risk_level: 4, is_cross_border: true, description: '港股宽基 ETF' },
  { symbol: '513180', name: '恒生科技ETF', exchange: 'SH', asset_class: 'qdii', asset_region: 'HK', risk_level: 5, is_cross_border: true, description: '港股科技主题 ETF' },
  { symbol: '513050', name: '中概互联网ETF', exchange: 'SH', asset_class: 'qdii', asset_region: 'CN_HK_US', risk_level: 5, is_cross_border: true, description: '中概互联网主题 ETF' },
  { symbol: '513100', name: '纳指ETF', exchange: 'SH', asset_class: 'qdii', asset_region: 'US', risk_level: 5, is_cross_border: true, description: '美国纳斯达克 100 ETF' },
  { symbol: '513500', name: '标普500ETF', exchange: 'SH', asset_class: 'qdii', asset_region: 'US', risk_level: 4, is_cross_border: true, description: '美国标普 500 ETF' },
  { symbol: '518880', name: '黄金ETF', exchange: 'SH', asset_class: 'gold', asset_region: 'CN', risk_level: 3, description: '黄金商品 ETF' },
  { symbol: '159934', name: '黄金ETF基金', exchange: 'SZ', asset_class: 'gold', asset_region: 'CN', risk_level: 3, description: '黄金商品 ETF' },
  { symbol: '511010', name: '国债ETF', exchange: 'SH', asset_class: 'bond', asset_region: 'CN', risk_level: 2, description: '国债 ETF' },
  { symbol: '511260', name: '十年国债ETF', exchange: 'SH', asset_class: 'bond', asset_region: 'CN', risk_level: 2, description: '长期国债 ETF' },
  { symbol: '511880', name: '银华日利ETF', exchange: 'SH', asset_class: 'cash', asset_region: 'CN', risk_level: 1, description: '货币现金管理 ETF' },
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
    ElMessage.success(`已导入 ${result.inserted_or_updated} 条精选 ETF`)
    await refresh()
  } catch (error) {
    ElMessage.error(errorMessage(error, '导入失败'))
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
    ElMessage.error(errorMessage(error, '导入失败'))
  } finally {
    actionLoading.value = false
  }
}

async function toggleAsset(symbol: string, enabled: string | number | boolean) {
  togglingSymbol.value = symbol
  try {
    await updateAsset(symbol, { enabled: Boolean(enabled) })
    const asset = assets.value.find((item) => item.symbol === symbol)
    if (asset) asset.enabled = Boolean(enabled)
    ElMessage.success(`已${enabled ? '启用' : '停用'} ${symbol}`)
  } catch (error) {
    ElMessage.error(errorMessage(error, '更新失败'))
    await refresh()
  } finally {
    togglingSymbol.value = ''
  }
}

async function copyEnabledSymbols() {
  const text = enabledAssets.value.map((item) => item.symbol).join(',')
  if (!text) {
    ElMessage.warning('当前没有已启用 ETF')
    return
  }
  await navigator.clipboard.writeText(text)
  ElMessage.success('已复制已启用 ETF 代码')
}

function parseImportText(value: string): AssetUpsertItem[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [symbol, name, exchange, assetClass, assetRegion, riskLevel, description] = line.split(/[,\t，]/).map((item) => item.trim())
      const region = assetRegion || 'CN'
      return {
        symbol,
        name,
        exchange: exchange || null,
        asset_class: assetClass || 'equity',
        asset_region: region,
        risk_level: Number(riskLevel || 3),
        description: description || null,
        currency: 'CNY',
        is_cross_border: ['US', 'HK', 'GLOBAL', 'CN_HK_US'].includes(region),
        enabled: true,
      }
    })
    .filter((item) => item.symbol && item.name)
}

const enabledAssets = computed(() => assets.value.filter((item) => item.enabled))
const crossBorderCount = computed(() => assets.value.filter((item) => item.is_cross_border).length)
const highRiskCount = computed(() => assets.value.filter((item) => Number(item.risk_level || 0) >= 5).length)

const assetClassOptions = computed(() =>
  Array.from(new Set(assets.value.map((item) => item.asset_class).filter(Boolean))).sort(),
)

const assetRegionOptions = computed(() =>
  Array.from(new Set(assets.value.map((item) => item.asset_region).filter(Boolean) as string[])).sort(),
)

const filteredAssets = computed(() =>
  assets.value.filter((item) => {
    const searchText = `${item.symbol} ${item.name} ${item.description || ''}`.toLowerCase()
    const matchesKeyword = !keyword.value || searchText.includes(keyword.value.toLowerCase())
    const matchesEnabled =
      enabledFilter.value === 'all' ||
      (enabledFilter.value === 'enabled' && item.enabled) ||
      (enabledFilter.value === 'disabled' && !item.enabled)
    const matchesClass = assetClassFilter.value === 'all' || item.asset_class === assetClassFilter.value
    const matchesRegion = assetRegionFilter.value === 'all' || item.asset_region === assetRegionFilter.value
    const matchesRisk = Number(item.risk_level || 0) <= riskLevelMax.value
    const matchesCrossBorder =
      crossBorderFilter.value === 'all' ||
      (crossBorderFilter.value === 'yes' && item.is_cross_border) ||
      (crossBorderFilter.value === 'no' && !item.is_cross_border)
    return matchesKeyword && matchesEnabled && matchesClass && matchesRegion && matchesRisk && matchesCrossBorder
  }),
)

function assetClassText(value: string | null) {
  const map: Record<string, string> = {
    equity: '权益',
    bond: '债券',
    gold: '黄金',
    commodity: '商品',
    cash: '货币',
    qdii: 'QDII',
  }
  return map[value || ''] || value || '-'
}

function regionText(value: string | null) {
  const map: Record<string, string> = {
    CN: '中国内地',
    HK: '港股',
    US: '美国',
    GLOBAL: '全球',
    CN_HK_US: '中概/港美',
  }
  return map[value || ''] || value || '-'
}

function riskText(value: number) {
  const risk = Number(value || 0)
  if (risk <= 1) return 'R1 很低'
  if (risk === 2) return 'R2 较低'
  if (risk === 3) return 'R3 中等'
  if (risk === 4) return 'R4 较高'
  return 'R5 高'
}

function riskTagType(value: number) {
  const risk = Number(value || 0)
  if (risk <= 2) return 'success'
  if (risk === 3) return 'info'
  if (risk === 4) return 'warning'
  return 'danger'
}

function errorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (detail) return detail
  return error instanceof Error ? error.message : fallback
}
</script>
