<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>风控与调仓生成</h2>
        <div>
          <el-button :loading="actionLoading" @click="runRiskCheck">执行风控</el-button>
          <el-button type="primary" :loading="actionLoading" @click="runOrderGeneration">生成调仓单</el-button>
        </div>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="运行 ID">
          <el-input-number v-model="runId" :min="1" />
          <span class="form-note">填写策略运行后生成的 run_id。</span>
        </el-form-item>
        <el-form-item label="组合市值">
          <el-input-number v-model="portfolioValue" :min="1000" :step="10000" />
        </el-form-item>
      </el-form>
    </section>
    <section class="panel span-6">
      <h2>风控结果</h2>
      <el-table :data="riskResults" height="520">
        <el-table-column prop="run_id" label="运行 ID" width="90" />
        <el-table-column prop="rule_code" label="规则" width="180" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="before_value" label="调整前" width="120" />
        <el-table-column prop="after_value" label="调整后" width="120" />
        <el-table-column prop="message" label="说明" min-width="220" />
      </el-table>
    </section>
    <section class="panel span-6">
      <h2>调仓单</h2>
      <el-table :data="orders" height="520">
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="action" label="方向" width="110" />
        <el-table-column prop="target_weight" label="目标权重" width="120" />
        <el-table-column prop="estimated_amount" label="估算金额" width="140" />
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { checkRisk, fetchRebalanceOrders, fetchRiskResults, generateRebalanceOrders, type RebalanceOrder, type RiskResult } from '../api/client'

const riskResults = ref<RiskResult[]>([])
const orders = ref<RebalanceOrder[]>([])
const loading = ref(true)
const actionLoading = ref(false)
const runId = ref(1)
const portfolioValue = ref(100000)

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    ;[riskResults.value, orders.value] = await Promise.all([fetchRiskResults(), fetchRebalanceOrders()])
  } finally {
    loading.value = false
  }
}

async function runRiskCheck() {
  await withAction('风控检查完成', () => checkRisk({ run_id: runId.value }))
}

async function runOrderGeneration() {
  await withAction('调仓单生成完成', () => generateRebalanceOrders({ run_id: runId.value, portfolio_value: portfolioValue.value }))
}

async function withAction(successMessage: string, action: () => Promise<unknown>) {
  actionLoading.value = true
  try {
    await action()
    ElMessage.success(successMessage)
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '执行失败')
  } finally {
    actionLoading.value = false
  }
}
</script>
