<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>AI 投研委员会</h2>
          <p class="section-note">多角色 Agent 基于本地 ETF 数据分析，DeepSeek 负责综合成中文结论；当前只生成建议，不自动下单。</p>
        </div>
        <div class="header-actions">
          <el-input v-model="symbol" placeholder="ETF 代码" class="symbol-input" />
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
          <el-switch v-model="useLlm" active-text="DeepSeek 总结" />
          <el-button type="primary" :loading="loading" @click="runAnalysis">运行分析</el-button>
        </div>
      </div>
      <el-alert
        v-if="analysis?.warnings.length"
        type="warning"
        :closable="false"
        show-icon
        :title="analysis.warnings.join('；')"
      />
    </section>

    <section class="panel span-3">
      <div class="metric">综合建议<strong>{{ analysis?.final_action || '-' }}</strong><span>{{ analysis?.name || symbol }}</span></div>
    </section>
    <section class="panel span-3">
      <div class="metric">综合评分<strong>{{ analysis?.final_score ?? '-' }}</strong><span>0-100</span></div>
    </section>
    <section class="panel span-3">
      <div class="metric">AI 总结<strong>{{ analysis?.llm_used ? '已启用' : '规则生成' }}</strong><span>{{ analysis?.llm_model || '未配置模型' }}</span></div>
    </section>
    <section class="panel span-3">
      <div class="metric">数据状态<strong>{{ dataStatusText }}</strong><span>{{ analysis?.start_date || '-' }} 至 {{ analysis?.end_date || '-' }}</span></div>
    </section>

    <section class="panel span-12">
      <h2>复合经理结论</h2>
      <div class="report-text">
        <p>{{ analysis?.final_summary || '请输入 ETF 代码并运行分析。' }}</p>
        <p v-if="analysis?.manager_commentary && analysis.manager_commentary !== analysis.final_summary">{{ analysis.manager_commentary }}</p>
      </div>
    </section>

    <section v-for="agent in analysis?.agents || []" :key="agent.role" class="panel span-4">
      <div class="panel-header">
        <h2>{{ agent.title }}</h2>
        <el-tag :type="scoreTag(agent.score)">{{ agent.stance }} · {{ agent.score }}</el-tag>
      </div>
      <p class="agent-summary">{{ agent.summary }}</p>
      <div class="agent-block">
        <strong>证据</strong>
        <ul>
          <li v-for="item in agent.evidence" :key="item">{{ item }}</li>
        </ul>
      </div>
      <div class="agent-block">
        <strong>风险</strong>
        <ul>
          <li v-for="item in agent.risks" :key="item">{{ item }}</li>
        </ul>
      </div>
      <el-divider />
      <div class="agent-action">{{ agent.suggestion }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyzeEtfAgents, type EtfAgentAnalysisResponse } from '../api/client'

const today = new Date().toISOString().slice(0, 10)
const lastYear = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
const symbol = ref('510300')
const dateRange = ref<[string, string]>([lastYear, today])
const useLlm = ref(true)
const loading = ref(false)
const analysis = ref<EtfAgentAnalysisResponse>()

const dataStatusText = computed(() => {
  if (!analysis.value) return '-'
  return analysis.value.data_status === 'ready' ? '可分析' : '缺行情'
})

async function runAnalysis() {
  const cleaned = symbol.value.trim()
  if (!cleaned) {
    ElMessage.warning('请输入 ETF 代码')
    return
  }
  loading.value = true
  try {
    analysis.value = await analyzeEtfAgents({
      symbol: cleaned,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      use_llm: useLlm.value,
    })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'AI 投研分析失败')
  } finally {
    loading.value = false
  }
}

function scoreTag(score: number) {
  if (score >= 75) return 'success'
  if (score >= 55) return 'info'
  if (score >= 40) return 'warning'
  return 'danger'
}
</script>
