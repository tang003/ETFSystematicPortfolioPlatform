<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>AI 投研委员会</h2>
          <p class="section-note">
            多角色 Agent 基于本地 ETF 数据分析，DeepSeek 负责综合成中文结论；当前只生成建议，不自动下单。
          </p>
        </div>
        <div class="header-actions">
          <el-input v-model="symbol" placeholder="ETF 代码" class="symbol-input" />
          <el-segmented v-model="datePreset" :options="analysisPresetOptions" @change="applyPreset" />
          <el-date-picker
            v-if="datePreset === 'custom'"
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :clearable="false"
          />
          <el-switch v-model="autoSync" active-text="自动补全数据" />
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
        <p v-if="analysis?.manager_commentary && analysis.manager_commentary !== analysis.final_summary">
          {{ analysis.manager_commentary }}
        </p>
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

    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>最近分析记录</h2>
          <p class="section-note">每次运行都会自动保存，后续可用于复盘和对比。</p>
        </div>
        <el-button @click="loadHistory">刷新记录</el-button>
      </div>
      <el-table :data="history" size="small" empty-text="暂无历史记录">
        <el-table-column prop="created_at" label="生成时间" min-width="160" />
        <el-table-column prop="symbol" label="代码" width="90" />
        <el-table-column prop="name" label="名称" min-width="130" />
        <el-table-column prop="final_action" label="建议" min-width="120" />
        <el-table-column prop="final_score" label="评分" width="90" />
        <el-table-column label="AI" width="90">
          <template #default="{ row }">{{ row.llm_used ? 'DeepSeek' : '规则' }}</template>
        </el-table-column>
        <el-table-column prop="final_summary" label="结论摘要" min-width="260" show-overflow-tooltip />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" @click="useHistory(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  analyzeEtfAgents,
  fetchEtfAgentAnalysisHistory,
  type EtfAgentAnalysisLog,
  type EtfAgentAnalysisResponse,
} from '../api/client'
import { analysisPresetOptions, buildPresetRange, type AnalysisPreset } from '../datePresets'

const symbol = ref('510300')
const datePreset = ref<AnalysisPreset>('1y')
const dateRange = ref<[string, string]>(buildPresetRange(datePreset.value))
const useLlm = ref(true)
const autoSync = ref(true)
const loading = ref(false)
const analysis = ref<EtfAgentAnalysisResponse>()
const history = ref<EtfAgentAnalysisLog[]>([])

const dataStatusText = computed(() => {
  if (!analysis.value) return '-'
  return analysis.value.data_status === 'ready' ? '可分析' : '缺行情'
})

onMounted(loadHistory)

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
      auto_sync: autoSync.value,
    })
    await loadHistory()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'AI 投研分析失败')
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  history.value = await fetchEtfAgentAnalysisHistory({ symbol: symbol.value.trim() || undefined, limit: 20 })
}

function useHistory(row: EtfAgentAnalysisLog) {
  analysis.value = row
  symbol.value = row.symbol
  datePreset.value = 'custom'
  dateRange.value = [row.start_date, row.end_date]
}

function applyPreset() {
  if (datePreset.value !== 'custom') {
    dateRange.value = buildPresetRange(datePreset.value)
  }
}

function scoreTag(score: number) {
  if (score >= 75) return 'success'
  if (score >= 55) return 'info'
  if (score >= 40) return 'warning'
  return 'danger'
}
</script>
