<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>因子研究实验室</h2>
        <el-button type="primary" :loading="actionLoading" @click="runResearch">运行研究</el-button>
      </div>
      <el-form class="action-form" label-width="100px">
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item label="前瞻天数">
          <el-input-number v-model="forwardDays" :min="1" :max="250" />
          <span class="form-note">用于计算未来收益。</span>
        </el-form-item>
        <el-form-item label="分组数量">
          <el-input-number v-model="quantiles" :min="2" :max="10" />
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-3">
      <div class="metric">样本数量<strong>{{ result?.sample_count ?? 0 }}</strong></div>
    </section>
    <section class="panel span-3">
      <div class="metric">因子数量<strong>{{ result?.factor_count ?? 0 }}</strong></div>
    </section>
    <section class="panel span-3">
      <div class="metric">有效因子<strong>{{ effectiveCount }}</strong></div>
    </section>
    <section class="panel span-3">
      <div class="metric">前瞻天数<strong>{{ result?.forward_days ?? forwardDays }}</strong></div>
    </section>

    <section class="panel span-7">
      <h2>IC / Rank IC</h2>
      <el-table :data="result?.ic_metrics || []" height="420">
        <el-table-column prop="factor_name" label="因子" width="160" />
        <el-table-column prop="observations" label="观察期" width="100" />
        <el-table-column prop="mean_ic" label="平均 IC" width="120" />
        <el-table-column prop="mean_rank_ic" label="平均 Rank IC" width="140" />
        <el-table-column prop="positive_ic_ratio" label="IC 胜率" width="120" />
        <el-table-column label="判断" width="110">
          <template #default="{ row }"><el-tag :type="row.effective ? 'success' : 'info'">{{ row.effective ? '有效' : '观察' }}</el-tag></template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-5">
      <h2>因子相关性</h2>
      <el-table :data="correlationRows" height="420">
        <el-table-column prop="pair" label="因子组合" min-width="180" />
        <el-table-column prop="correlation" label="相关性" width="120" />
      </el-table>
    </section>

    <section class="panel span-12">
      <h2>分组未来收益</h2>
      <el-table :data="result?.quantile_returns || []" height="420">
        <el-table-column prop="factor_name" label="因子" width="170" />
        <el-table-column prop="quantile" label="分组" width="90" />
        <el-table-column prop="mean_forward_return" label="平均未来收益" width="150" />
        <el-table-column prop="observations" label="样本数" width="120" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { researchFactors, type FactorResearchResult } from '../api/client'

const loading = ref(false)
const actionLoading = ref(false)
const today = new Date().toISOString().slice(0, 10)
const lastYear = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([lastYear, today])
const forwardDays = ref(20)
const quantiles = ref(3)
const result = ref<FactorResearchResult>()

const effectiveCount = computed(() => result.value?.ic_metrics.filter((item) => item.effective).length ?? 0)
const correlationRows = computed(() => {
  const rows = result.value?.correlations || []
  return rows
    .filter((item) => item.factor_x < item.factor_y)
    .map((item) => ({ pair: `${item.factor_x} / ${item.factor_y}`, correlation: item.correlation }))
    .sort((a, b) => Math.abs(Number(b.correlation || 0)) - Math.abs(Number(a.correlation || 0)))
})

async function runResearch() {
  actionLoading.value = true
  loading.value = true
  try {
    result.value = await researchFactors({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      forward_days: forwardDays.value,
      quantiles: quantiles.value,
    })
    ElMessage.success('因子研究完成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '因子研究失败')
  } finally {
    actionLoading.value = false
    loading.value = false
  }
}
</script>
