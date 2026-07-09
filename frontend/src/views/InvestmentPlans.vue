<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>创建定投计划</h2>
        <div>
          <el-button type="primary" :loading="actionLoading" @click="createPlan">保存计划</el-button>
          <el-button type="success" :disabled="!selectedPlanId" :loading="actionLoading" @click="runAnalysis">生成本期建议</el-button>
        </div>
      </div>
      <el-form class="action-form" label-width="100px">
        <el-form-item label="计划名称">
          <el-input v-model="form.plan_name" placeholder="例如：核心 ETF 月定投" />
        </el-form-item>
        <el-form-item label="运行 ID">
          <el-input-number v-model="form.run_id" :min="1" />
          <span class="form-note">用于读取某次目标组合。</span>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="定投期数">
          <el-input-number v-model="form.months" :min="1" :max="360" />
        </el-form-item>
        <el-form-item label="每期金额">
          <el-input-number v-model="form.monthly_amount" :min="100" :step="500" />
        </el-form-item>
        <el-form-item label="本期期数">
          <el-input-number v-model="periodNo" :min="1" :max="form.months" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="可记录资金来源、目标或纪律说明" />
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-5">
      <h2>计划列表</h2>
      <el-table :data="plans" height="420" highlight-current-row @current-change="selectPlan">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="plan_name" label="名称" min-width="160" />
        <el-table-column prop="monthly_amount" label="每期金额" width="120" />
        <el-table-column prop="months" label="期数" width="80" />
        <el-table-column prop="total_budget" label="总预算" width="120" />
      </el-table>
    </section>

    <section class="panel span-7">
      <h2>本期定投建议</h2>
      <el-table :data="suggestions" height="420">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="suggested_amount" label="建议金额" width="130" />
        <el-table-column prop="current_weight" label="当前权重" width="120" />
        <el-table-column prop="target_weight" label="目标权重" width="120" />
        <el-table-column prop="gap_weight" label="缺口" width="100" />
        <el-table-column prop="reason" label="原因" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  analyzeInvestmentPlan,
  createInvestmentPlan,
  fetchInvestmentPlanSuggestions,
  fetchInvestmentPlans,
  type InvestmentPlan,
  type InvestmentPlanSuggestion,
} from '../api/client'

const loading = ref(false)
const actionLoading = ref(false)
const plans = ref<InvestmentPlan[]>([])
const suggestions = ref<InvestmentPlanSuggestion[]>([])
const selectedPlanId = ref<number | null>(null)
const periodNo = ref(1)
const form = reactive({
  plan_name: '核心 ETF 月定投',
  run_id: 1,
  start_date: new Date().toISOString().slice(0, 10),
  months: 12,
  monthly_amount: 3000,
  note: '',
})

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    plans.value = await fetchInvestmentPlans()
    if (!selectedPlanId.value && plans.value.length) {
      selectedPlanId.value = plans.value[0].id
      suggestions.value = await fetchInvestmentPlanSuggestions(plans.value[0].id)
    }
  } finally {
    loading.value = false
  }
}

async function createPlan() {
  actionLoading.value = true
  try {
    const plan = await createInvestmentPlan({ ...form })
    selectedPlanId.value = plan.id
    ElMessage.success('定投计划已保存')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    actionLoading.value = false
  }
}

async function runAnalysis() {
  if (!selectedPlanId.value) return
  actionLoading.value = true
  try {
    suggestions.value = await analyzeInvestmentPlan(selectedPlanId.value, {
      period_no: periodNo.value,
      suggestion_date: new Date().toISOString().slice(0, 10),
    })
    ElMessage.success('本期定投建议已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '分析失败')
  } finally {
    actionLoading.value = false
  }
}

async function selectPlan(row: InvestmentPlan | undefined) {
  if (!row) return
  selectedPlanId.value = row.id
  form.run_id = row.run_id || form.run_id
  form.months = row.months
  form.monthly_amount = Number(row.monthly_amount)
  periodNo.value = Math.min(periodNo.value, row.months)
  suggestions.value = await fetchInvestmentPlanSuggestions(row.id)
}
</script>
