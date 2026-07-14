<template>
  <div class="page-grid">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>策略管理</h2>
          <p class="section-note">维护内置 ETF 策略的参数、启用状态和运行入口。新增策略后，后端会按策略代码读取配置生成目标组合。</p>
        </div>
        <div class="task-tags">
          <el-button @click="loadStrategies">刷新</el-button>
          <el-button type="primary" @click="openCreate">新增策略</el-button>
        </div>
      </div>
      <el-table :data="strategies" v-loading="loading" height="430">
        <el-table-column prop="strategy_code" label="策略代码" min-width="190" />
        <el-table-column prop="strategy_name" label="策略名称" min-width="180" />
        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column prop="rebalance_frequency" label="调仓频率" width="110" />
        <el-table-column label="风险画像" width="110">
          <template #default="{ row }">{{ row.config?.risk_profile || '-' }}</template>
        </el-table-column>
        <el-table-column label="目标权重" min-width="260">
          <template #default="{ row }">{{ targetWeightText(row.config?.target_weights) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link :type="row.enabled ? 'warning' : 'success'" @click="toggleStrategy(row)">
              {{ row.enabled ? '停用' : '启用' }}
            </el-button>
            <el-button link type="primary" :loading="runningCode === row.strategy_code" @click="run(row.strategy_code)">运行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-5">
      <h2>当前策略体系</h2>
      <div class="insight-list">
        <div class="insight-item">
          <span>执行引擎</span>
          <p>当前正式接入的是因子轮动引擎，策略通过目标权重、风险画像和区域偏好产生差异。</p>
        </div>
        <div class="insight-item">
          <span>新增方式</span>
          <p>新增策略时至少填写策略代码、名称和目标权重；更复杂的策略需要后端继续扩展专属引擎。</p>
        </div>
        <div class="insight-item">
          <span>使用建议</span>
          <p>普通用户优先使用核心 ETF 轮动；风险偏高可试进取权益，回撤敏感可试防守全天候。</p>
        </div>
      </div>
    </section>

    <section class="panel span-7">
      <h2>策略参数说明</h2>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="equity_primary">第一名权益 ETF 的目标权重。</el-descriptions-item>
        <el-descriptions-item label="equity_secondary">第二名权益 ETF 的目标权重。</el-descriptions-item>
        <el-descriptions-item label="defense">债券或黄金等防守资产目标权重。</el-descriptions-item>
        <el-descriptions-item label="cash">现金或货币 ETF 缓冲权重。</el-descriptions-item>
        <el-descriptions-item label="preferred_regions">可选，限制策略优先选择的区域，例如 US、GLOBAL、JP。</el-descriptions-item>
      </el-descriptions>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingCode ? '编辑策略' : '新增策略'" width="720px">
      <el-form label-width="108px">
        <el-form-item label="策略代码">
          <el-input v-model="form.strategy_code" :disabled="Boolean(editingCode)" placeholder="例如 low_volatility_rotation" />
        </el-form-item>
        <el-form-item label="策略名称">
          <el-input v-model="form.strategy_name" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="form.version" />
        </el-form-item>
        <el-form-item label="调仓频率">
          <el-select v-model="form.rebalance_frequency">
            <el-option label="月度" value="monthly" />
            <el-option label="季度" value="quarterly" />
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="目标权重">
          <div class="weight-grid">
            <label>权益 1<el-input-number v-model="weights.equity_primary" :min="0" :max="1" :step="0.05" /></label>
            <label>权益 2<el-input-number v-model="weights.equity_secondary" :min="0" :max="1" :step="0.05" /></label>
            <label>防守<el-input-number v-model="weights.defense" :min="0" :max="1" :step="0.05" /></label>
            <label>现金<el-input-number v-model="weights.cash" :min="0" :max="1" :step="0.05" /></label>
          </div>
          <span class="form-note">合计不是 100% 时，后端会自动归一化。</span>
        </el-form-item>
        <el-form-item label="风险画像">
          <el-select v-model="riskProfile">
            <el-option label="均衡" value="balanced" />
            <el-option label="进取" value="aggressive" />
            <el-option label="防守" value="defensive" />
            <el-option label="全球" value="global" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域偏好">
          <el-input v-model="preferredRegions" placeholder="可选，例如 US,GLOBAL,JP；留空则不限制" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveStrategy">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createStrategy, fetchStrategies, runStrategy, updateStrategy, type StrategyConfig } from '../api/client'

const strategies = ref<StrategyConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingCode = ref('')
const runningCode = ref('')
const riskProfile = ref('balanced')
const preferredRegions = ref('')
const description = ref('')
const weights = reactive({
  equity_primary: 0.4,
  equity_secondary: 0.25,
  defense: 0.25,
  cash: 0.1,
})
const form = reactive({
  strategy_code: '',
  strategy_name: '',
  version: '0.1.0',
  rebalance_frequency: 'monthly',
  enabled: true,
})

onMounted(loadStrategies)

async function loadStrategies() {
  loading.value = true
  try {
    strategies.value = await fetchStrategies()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingCode.value = ''
  Object.assign(form, { strategy_code: '', strategy_name: '', version: '0.1.0', rebalance_frequency: 'monthly', enabled: true })
  Object.assign(weights, { equity_primary: 0.4, equity_secondary: 0.25, defense: 0.25, cash: 0.1 })
  riskProfile.value = 'balanced'
  preferredRegions.value = ''
  description.value = ''
  dialogVisible.value = true
}

function openEdit(strategy: StrategyConfig) {
  editingCode.value = strategy.strategy_code
  Object.assign(form, {
    strategy_code: strategy.strategy_code,
    strategy_name: strategy.strategy_name,
    version: strategy.version,
    rebalance_frequency: strategy.rebalance_frequency,
    enabled: strategy.enabled,
  })
  const targetWeights = (strategy.config?.target_weights || {}) as Record<string, unknown>
  Object.assign(weights, {
    equity_primary: Number(targetWeights.equity_primary ?? 0.4),
    equity_secondary: Number(targetWeights.equity_secondary ?? 0.25),
    defense: Number(targetWeights.defense ?? 0.25),
    cash: Number(targetWeights.cash ?? 0.1),
  })
  riskProfile.value = String(strategy.config?.risk_profile || 'balanced')
  preferredRegions.value = Array.isArray(strategy.config?.preferred_regions) ? strategy.config.preferred_regions.join(',') : ''
  description.value = String(strategy.config?.description || '')
  dialogVisible.value = true
}

async function saveStrategy() {
  saving.value = true
  try {
    const payload = {
      strategy_name: form.strategy_name,
      version: form.version,
      rebalance_frequency: form.rebalance_frequency,
      enabled: form.enabled,
      config: buildConfig(),
    }
    if (editingCode.value) {
      await updateStrategy(editingCode.value, payload)
    } else {
      await createStrategy({ strategy_code: form.strategy_code, ...payload })
    }
    ElMessage.success('策略已保存')
    dialogVisible.value = false
    await loadStrategies()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存策略失败')
  } finally {
    saving.value = false
  }
}

async function toggleStrategy(strategy: StrategyConfig) {
  await updateStrategy(strategy.strategy_code, { enabled: !strategy.enabled })
  ElMessage.success(strategy.enabled ? '策略已停用' : '策略已启用')
  await loadStrategies()
}

async function run(strategyCode: string) {
  runningCode.value = strategyCode
  try {
    const result = await runStrategy({ strategy_code: strategyCode, run_type: 'manual' })
    ElMessage.success(`策略运行完成，run_id=${String(result.run_id ?? '-')}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '策略运行失败')
  } finally {
    runningCode.value = ''
  }
}

function buildConfig() {
  const regions = preferredRegions.value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean)
  return {
    engine: 'factor_rotation',
    risk_profile: riskProfile.value,
    target_weights: {
      equity_primary: weights.equity_primary,
      equity_secondary: weights.equity_secondary,
      defense: weights.defense,
      cash: weights.cash,
    },
    preferred_regions: regions.length ? regions : undefined,
    description: description.value,
  }
}

function targetWeightText(value: unknown) {
  const weightsValue = (value || {}) as Record<string, unknown>
  const parts = [
    ['权益1', weightsValue.equity_primary],
    ['权益2', weightsValue.equity_secondary],
    ['防守', weightsValue.defense],
    ['现金', weightsValue.cash],
  ]
  return parts.map(([label, weight]) => `${label} ${percent(weight)}`).join(' / ')
}

function percent(value: unknown) {
  if (value == null || value === '') return '-'
  return `${(Number(value) * 100).toFixed(0)}%`
}
</script>

<style scoped>
.weight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 10px;
  width: 100%;
}

.weight-grid label {
  display: grid;
  gap: 6px;
  color: #52627a;
  font-size: 13px;
}
</style>
