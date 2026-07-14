<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>ETF 池管理</h2>
          <p class="section-note">维护 ETF 基础池和研究池；基础池保存 ETF 档案，启用后才进入行情、因子、策略和回测流程。</p>
        </div>
        <div class="header-actions">
          <el-button :loading="actionLoading" @click="syncUniverse">同步 ETF 基础池</el-button>
          <el-button :loading="actionLoading" @click="syncProfiles">补全当前筛选资料</el-button>
          <el-button type="primary" :loading="actionLoading" @click="importPresetAssets">导入精选示例池</el-button>
          <el-button @click="copyEnabledSymbols">复制已启用代码</el-button>
        </div>
      </div>

      <div class="summary-grid asset-summary">
        <div class="metric">ETF 总数<strong>{{ assets.length }}</strong></div>
        <div class="metric">启用研究<strong>{{ enabledAssets.length }}</strong></div>
        <div class="metric">跨境 ETF<strong>{{ crossBorderCount }}</strong></div>
        <div class="metric">资料较完整<strong>{{ completeProfileCount }}</strong></div>
        <div class="metric">交易性偏弱<strong>{{ weakTradabilityCount }}</strong></div>
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
      <el-form label-width="92px">
        <el-form-item label="导入内容">
          <el-input
            v-model="importText"
            type="textarea"
            :rows="13"
            placeholder="每行一只 ETF：代码,名称,交易所,资产类别,区域,风险等级,基金公司,跟踪指数,规模亿元,管理费%,托管费%,说明"
          />
        </el-form-item>
        <el-form-item label="格式示例">
          <div class="source-hint">
            <p>510300,沪深300ETF,SH,equity,CN,4,华泰柏瑞基金,沪深300,890,0.50,0.10,A股核心宽基</p>
            <p>513100,纳指ETF,SH,qdii,US,5,国泰基金,纳斯达克100,120,0.80,0.20,美股科技宽基</p>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="actionLoading" @click="submitImport">批量导入到 ETF 池</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-4">
      <div class="panel-header">
        <div>
          <h2>同步日志</h2>
          <p class="section-note">记录最近 ETF 基础池和主资料补全结果。</p>
        </div>
      </div>
      <el-table :data="syncLogs" height="260" empty-text="暂无补全日志">
        <el-table-column label="时间" min-width="140">
          <template #default="{ row }">{{ timeText(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="类型" width="86">
          <template #default="{ row }">{{ syncTypeText(row.sync_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="82">
          <template #default="{ row }">
            <el-tag :type="syncLogTag(row.status)" size="small">{{ syncLogStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" min-width="160">
          <template #default="{ row }">补全 {{ row.updated }} / 跳过 {{ row.skipped }} / 失败 {{ row.failed }}</template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-8">
      <div class="panel-header">
        <div>
          <h2>ETF 主数据</h2>
          <p class="section-note">筛选后 {{ filteredAssets.length }} 只，当前显示 {{ displayedAssets.length }} 只；资料完整度越高，ETF 对比、AI 投研和报告质量越好。</p>
        </div>
        <div class="task-tags">
          <el-tag type="success">启用 {{ enabledAssets.length }}</el-tag>
          <el-tag type="info">筛选 {{ filteredAssets.length }}</el-tag>
        </div>
      </div>
      <el-form class="action-form assets-filter-form" label-width="84px">
        <el-form-item label="搜索">
          <el-input v-model="keyword" clearable placeholder="代码 / 名称 / 指数 / 基金公司 / 说明" />
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
        <el-form-item label="资料完整">
          <el-select v-model="profileFilter">
            <el-option label="全部" value="all" />
            <el-option label="较完整" value="complete" />
            <el-option label="待补充" value="missing" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险上限">
          <el-slider v-model="riskLevelMax" :min="1" :max="5" show-stops />
        </el-form-item>
        <el-form-item label="评分下限">
          <el-slider v-model="tradabilityScoreMin" :min="0" :max="100" :step="10" show-stops />
        </el-form-item>
      </el-form>

      <el-table :data="displayedAssets" height="650" empty-text="暂无 ETF，先导入示例池或同步 ETF 基础池">
        <el-table-column prop="symbol" label="代码" width="100" fixed />
        <el-table-column prop="name" label="名称" min-width="150" fixed />
        <el-table-column label="资料" width="95">
          <template #default="{ row }">
            <el-tag :type="profileScore(row) >= 70 ? 'success' : profileScore(row) >= 40 ? 'warning' : 'danger'" size="small">
              {{ profileScore(row) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="跟踪指数" min-width="150">
          <template #default="{ row }">{{ row.tracking_index || '-' }}</template>
        </el-table-column>
        <el-table-column label="基金公司" min-width="140">
          <template #default="{ row }">{{ row.fund_company || '-' }}</template>
        </el-table-column>
        <el-table-column label="规模" width="120">
          <template #default="{ row }">{{ fundSizeText(row.fund_size) }}</template>
        </el-table-column>
        <el-table-column label="费率" width="120">
          <template #default="{ row }">{{ feeText(row.expense_ratio ?? totalFee(row)) }}</template>
        </el-table-column>
        <el-table-column label="类别" width="100">
          <template #default="{ row }"><el-tag size="small">{{ assetClassText(row.asset_class) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="区域" width="110">
          <template #default="{ row }">{{ regionText(row.asset_region) }}</template>
        </el-table-column>
        <el-table-column label="风险" width="110">
          <template #default="{ row }">
            <el-tag :type="riskTagType(row.risk_level)" size="small">{{ riskText(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="交易性" width="130">
          <template #default="{ row }">
            <el-tooltip :content="tradabilityNotes(row.symbol)" placement="top">
              <el-tag :type="scoreTagType(tradabilityScore(row.symbol))" size="small">
                {{ tradabilityScoreText(row.symbol) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" :loading="togglingSymbol === row.symbol" @change="(value: string | number | boolean) => toggleAsset(row.symbol, value)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openProfile(row)">编辑</el-button>
            <el-button link type="primary" @click="$router.push(`/etf-detail/${row.symbol}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="profileDialogVisible" title="编辑 ETF 资料" width="620px">
      <el-form v-if="profileForm" label-width="100px">
        <el-form-item label="代码">{{ profileForm.symbol }} {{ profileForm.name }}</el-form-item>
        <el-form-item label="基金公司"><el-input v-model="profileForm.fund_company" /></el-form-item>
        <el-form-item label="跟踪指数"><el-input v-model="profileForm.tracking_index" /></el-form-item>
        <el-form-item label="上市日期">
          <el-date-picker v-model="profileForm.listing_date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="规模(亿元)"><el-input-number v-model="profileForm.fund_size_yi" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="管理费%"><el-input-number v-model="profileForm.management_fee_percent" :min="0" :precision="4" /></el-form-item>
        <el-form-item label="托管费%"><el-input-number v-model="profileForm.custody_fee_percent" :min="0" :precision="4" /></el-form-item>
        <el-form-item label="综合费率%"><el-input-number v-model="profileForm.expense_ratio_percent" :min="0" :precision="4" /></el-form-item>
        <el-form-item label="跟踪误差%"><el-input-number v-model="profileForm.tracking_error_percent" :min="0" :precision="4" /></el-form-item>
        <el-form-item label="溢价率%"><el-input-number v-model="profileForm.latest_premium_rate_percent" :precision="4" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="profileForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  batchUpsertAssets,
  fetchAssets,
  fetchAssetSyncLogs,
  scoreEtfTradability,
  seedCuratedAssets,
  syncAssetProfiles,
  syncAssetUniverse,
  updateAsset,
  type Asset,
  type AssetSyncLog,
  type AssetUpsertItem,
  type EtfCompareMetric,
} from '../api/client'

type ProfileForm = {
  symbol: string
  name: string
  fund_company: string | null
  tracking_index: string | null
  listing_date: string | null
  fund_size_yi: number | null
  management_fee_percent: number | null
  custody_fee_percent: number | null
  expense_ratio_percent: number | null
  tracking_error_percent: number | null
  latest_premium_rate_percent: number | null
  description: string | null
}

const assets = ref<Asset[]>([])
const syncLogs = ref<AssetSyncLog[]>([])
const tradabilityMetrics = ref<Record<string, EtfCompareMetric>>({})
const loading = ref(true)
const actionLoading = ref(false)
const importText = ref('')
const keyword = ref('')
const enabledFilter = ref<'all' | 'enabled' | 'disabled'>('all')
const assetClassFilter = ref('all')
const assetRegionFilter = ref('all')
const profileFilter = ref<'all' | 'complete' | 'missing'>('all')
const riskLevelMax = ref(5)
const tradabilityScoreMin = ref(0)
const togglingSymbol = ref('')
const profileDialogVisible = ref(false)
const profileForm = ref<ProfileForm | null>(null)

const classQuickFilters = [
  { label: '权益', value: 'equity' },
  { label: '债券', value: 'bond' },
  { label: '黄金/商品', value: 'gold' },
  { label: '货币现金', value: 'cash' },
  { label: '跨境 QDII', value: 'qdii' },
]

const presetAssets: AssetUpsertItem[] = [
  { symbol: '510050', name: '上证50ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, tracking_index: '上证50', description: 'A股核心蓝筹 ETF' },
  { symbol: '510300', name: '沪深300ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, tracking_index: '沪深300', description: 'A股核心宽基 ETF' },
  { symbol: '510500', name: '中证500ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 4, tracking_index: '中证500', description: 'A股中盘宽基 ETF' },
  { symbol: '159915', name: '创业板ETF', exchange: 'SZ', asset_class: 'equity', asset_region: 'CN', risk_level: 5, tracking_index: '创业板指', description: '创业板成长 ETF' },
  { symbol: '588000', name: '科创50ETF', exchange: 'SH', asset_class: 'equity', asset_region: 'CN', risk_level: 5, tracking_index: '科创50', description: '科创板核心 ETF' },
  { symbol: '513050', name: '中概互联网ETF', exchange: 'SH', asset_class: 'qdii', asset_region: 'CN_HK_US', risk_level: 5, is_cross_border: true, tracking_index: '中证海外中国互联网', description: '中概互联网主题 ETF' },
  { symbol: '513100', name: '纳指ETF', exchange: 'SH', asset_class: 'qdii', asset_region: 'US', risk_level: 5, is_cross_border: true, tracking_index: '纳斯达克100', description: '美国科技宽基 ETF' },
  { symbol: '518880', name: '黄金ETF', exchange: 'SH', asset_class: 'gold', asset_region: 'CN', risk_level: 3, tracking_index: '上海黄金交易所黄金现货', description: '黄金商品 ETF' },
  { symbol: '511010', name: '国债ETF', exchange: 'SH', asset_class: 'bond', asset_region: 'CN', risk_level: 2, tracking_index: '上证5年期国债', description: '国债 ETF' },
  { symbol: '511880', name: '银华日利ETF', exchange: 'SH', asset_class: 'cash', asset_region: 'CN', risk_level: 1, description: '货币现金管理 ETF' },
]

onMounted(refresh)

async function refresh() {
  try {
    const [assetRows, logRows] = await Promise.all([
      fetchAssets(),
      fetchAssetSyncLogs({ limit: 10 }),
    ])
    assets.value = assetRows
    syncLogs.value = logRows
  } finally {
    loading.value = false
  }
  void refreshTradabilityScores()
}

async function refreshTradabilityScores() {
  const preferred = assets.value.filter((item) => item.enabled).map((item) => item.symbol)
  const visible = filteredAssets.value.map((item) => item.symbol)
  const symbols = Array.from(new Set([...preferred, ...visible])).slice(0, 100)
  if (!symbols.length) {
    tradabilityMetrics.value = {}
    return
  }
  try {
    const rows = await scoreEtfTradability({ symbols })
    tradabilityMetrics.value = Object.fromEntries(rows.map((item) => [item.symbol, item]))
  } catch {
    tradabilityMetrics.value = {}
  }
}

async function importPresetAssets() {
  actionLoading.value = true
  try {
    const result = await seedCuratedAssets()
    ElMessage.success(`已导入 ${result.inserted_or_updated} 条精选 ETF`)
    await refresh()
  } catch (error) {
    ElMessage.error(errorMessage(error, '导入失败'))
  } finally {
    actionLoading.value = false
  }
}

async function syncUniverse() {
  actionLoading.value = true
  try {
    const result = await syncAssetUniverse({ source: 'auto' })
    ElMessage.success(`已通过 ${result.source} 同步 ${result.inserted_or_updated} 只 ETF 到基础池，默认不启用研究`)
    await refresh()
  } catch (error) {
    ElMessage.error(errorMessage(error, '同步失败'))
  } finally {
    actionLoading.value = false
  }
}

async function syncProfiles() {
  const symbols = filteredAssets.value.map((item) => item.symbol).slice(0, 100)
  if (!symbols.length) {
    ElMessage.warning('当前筛选结果为空，无法补全资料')
    return
  }
  actionLoading.value = true
  try {
    const result = await syncAssetProfiles({
      source: 'auto',
      symbols,
      limit: symbols.length,
      preserve_existing: true,
    })
    ElMessage.success(`已补全 ${result.updated} 只 ETF，跳过 ${result.skipped} 只，失败 ${result.failed} 只`)
    await refresh()
  } catch (error) {
    ElMessage.error(errorMessage(error, '资料补全失败'))
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

function openProfile(asset: Asset) {
  profileForm.value = {
    symbol: asset.symbol,
    name: asset.name,
    fund_company: asset.fund_company || null,
    tracking_index: asset.tracking_index || null,
    listing_date: asset.listing_date || null,
    fund_size_yi: asset.fund_size ? Number(asset.fund_size) / 100000000 : null,
    management_fee_percent: toPercentNumber(asset.management_fee),
    custody_fee_percent: toPercentNumber(asset.custody_fee),
    expense_ratio_percent: toPercentNumber(asset.expense_ratio),
    tracking_error_percent: toPercentNumber(asset.tracking_error),
    latest_premium_rate_percent: toPercentNumber(asset.latest_premium_rate),
    description: asset.description || null,
  }
  profileDialogVisible.value = true
}

async function saveProfile() {
  if (!profileForm.value) return
  actionLoading.value = true
  try {
    const form = profileForm.value
    await updateAsset(form.symbol, {
      fund_company: form.fund_company,
      tracking_index: form.tracking_index,
      listing_date: form.listing_date,
      fund_size: form.fund_size_yi == null ? null : form.fund_size_yi * 100000000,
      management_fee: fromPercentNumber(form.management_fee_percent),
      custody_fee: fromPercentNumber(form.custody_fee_percent),
      expense_ratio: fromPercentNumber(form.expense_ratio_percent),
      tracking_error: fromPercentNumber(form.tracking_error_percent),
      latest_premium_rate: fromPercentNumber(form.latest_premium_rate_percent),
      description: form.description,
    })
    ElMessage.success('ETF 资料已保存')
    profileDialogVisible.value = false
    await refresh()
  } catch (error) {
    ElMessage.error(errorMessage(error, '保存失败'))
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
      const [symbol, name, exchange, assetClass, assetRegion, riskLevel, fundCompany, trackingIndex, fundSizeYi, managementFee, custodyFee, description] = line
        .split(/[,\t，]/)
        .map((item) => item.trim())
      const region = assetRegion || 'CN'
      return {
        symbol,
        name,
        exchange: exchange || null,
        asset_class: assetClass || 'equity',
        asset_region: region,
        risk_level: Number(riskLevel || 3),
        fund_company: fundCompany || null,
        tracking_index: trackingIndex || null,
        fund_size: fundSizeYi ? Number(fundSizeYi) * 100000000 : null,
        management_fee: fromPercentNumber(managementFee ? Number(managementFee) : null),
        custody_fee: fromPercentNumber(custodyFee ? Number(custodyFee) : null),
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
const completeProfileCount = computed(() => assets.value.filter((item) => profileScore(item) >= 70).length)
const weakTradabilityCount = computed(() => assets.value.filter((item) => {
  const score = tradabilityScore(item.symbol)
  return score !== null && score < 60
}).length)

const assetClassOptions = computed(() => Array.from(new Set(assets.value.map((item) => item.asset_class).filter(Boolean))).sort())
const assetRegionOptions = computed(() => Array.from(new Set(assets.value.map((item) => item.asset_region).filter(Boolean) as string[])).sort())

const filteredAssets = computed(() =>
  assets.value.filter((item) => {
    const searchText = `${item.symbol} ${item.name} ${item.tracking_index || ''} ${item.fund_company || ''} ${item.description || ''}`.toLowerCase()
    const matchesKeyword = !keyword.value || searchText.includes(keyword.value.toLowerCase())
    const matchesEnabled = enabledFilter.value === 'all' || (enabledFilter.value === 'enabled' && item.enabled) || (enabledFilter.value === 'disabled' && !item.enabled)
    const matchesClass = assetClassFilter.value === 'all' || item.asset_class === assetClassFilter.value
    const matchesRegion = assetRegionFilter.value === 'all' || item.asset_region === assetRegionFilter.value
    const matchesRisk = Number(item.risk_level || 0) <= riskLevelMax.value
    const score = tradabilityScore(item.symbol)
    const matchesTradability = score === null ? tradabilityScoreMin.value === 0 : score >= tradabilityScoreMin.value
    const pScore = profileScore(item)
    const matchesProfile = profileFilter.value === 'all' || (profileFilter.value === 'complete' && pScore >= 70) || (profileFilter.value === 'missing' && pScore < 70)
    return matchesKeyword && matchesEnabled && matchesClass && matchesRegion && matchesRisk && matchesTradability && matchesProfile
  }),
)

const displayedAssets = computed(() => filteredAssets.value.slice(0, 300))

function profileScore(asset: Asset) {
  const fields = [
    asset.fund_company,
    asset.tracking_index,
    asset.listing_date,
    asset.fund_size,
    asset.management_fee,
    asset.custody_fee,
    asset.expense_ratio,
    asset.tracking_error,
    asset.latest_premium_rate,
    asset.description,
  ]
  return Math.round((fields.filter((value) => value !== null && value !== undefined && value !== '').length / fields.length) * 100)
}

function assetClassText(value: string | null) {
  const map: Record<string, string> = { equity: '权益', bond: '债券', gold: '黄金', commodity: '商品', cash: '货币', qdii: 'QDII' }
  return map[value || ''] || value || '-'
}

function regionText(value: string | null) {
  const map: Record<string, string> = { CN: '中国内地', HK: '港股', US: '美国', GLOBAL: '全球', CN_HK_US: '中概/港美', JP: '日本', DE: '德国' }
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

function tradabilityScore(symbol: string) {
  const value = tradabilityMetrics.value[symbol]?.tradability_score
  return typeof value === 'number' ? value : null
}

function tradabilityScoreText(symbol: string) {
  const metric = tradabilityMetrics.value[symbol]
  if (!metric) return '未评分'
  return `${metric.tradability_score} ${metric.tradability_level}`
}

function tradabilityNotes(symbol: string) {
  const metric = tradabilityMetrics.value[symbol]
  if (!metric) return '暂无可交易性评分，请先同步行情。'
  return metric.tradability_notes.join('；')
}

function scoreTagType(value: number | null) {
  if (value === null) return 'info'
  if (value >= 80) return 'success'
  if (value >= 60) return 'info'
  if (value >= 40) return 'warning'
  return 'danger'
}

function syncLogTag(status: string) {
  if (status === 'success') return 'success'
  if (status === 'partial') return 'warning'
  return 'danger'
}

function syncLogStatusText(status: string) {
  const map: Record<string, string> = { success: '成功', partial: '部分', failed: '失败' }
  return map[status] || status
}

function syncTypeText(type: string) {
  const map: Record<string, string> = { profile: '资料', universe: '基础池' }
  return map[type] || type
}

function timeText(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}

function fundSizeText(value: string | null | undefined) {
  if (!value) return '-'
  return `${(Number(value) / 100000000).toFixed(2)} 亿`
}

function feeText(value: string | number | null | undefined) {
  if (value == null || value === '') return '-'
  return `${(Number(value) * 100).toFixed(3)}%`
}

function totalFee(asset: Asset) {
  const management = asset.management_fee ? Number(asset.management_fee) : 0
  const custody = asset.custody_fee ? Number(asset.custody_fee) : 0
  return management || custody ? management + custody : null
}

function toPercentNumber(value: string | null | undefined) {
  return value == null ? null : Number((Number(value) * 100).toFixed(4))
}

function fromPercentNumber(value: number | null | undefined) {
  return value == null ? null : value / 100
}

function errorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (detail) return detail
  return error instanceof Error ? error.message : fallback
}
</script>
