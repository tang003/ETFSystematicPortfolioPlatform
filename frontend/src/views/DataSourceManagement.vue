<template>
  <div class="page-grid">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>数据源管理</h2>
          <p class="section-note">统一查看行情、基金资料、交易日历和 AI 接口的配置状态。Token 只保存在后端，前端只展示脱敏结果。</p>
        </div>
        <el-button :loading="loading" @click="loadSettings">刷新状态</el-button>
      </div>
      <div class="summary-grid">
        <div class="metric">日历源<strong>{{ settings?.default_calendar_source || '-' }}</strong><span>交易日历</span></div>
        <div class="metric">行情源<strong>{{ settings?.default_market_source || '-' }}</strong><span>ETF 日线</span></div>
        <div class="metric">资料源<strong>{{ settings?.default_profile_source || '-' }}</strong><span>ETF 基础资料</span></div>
        <div class="metric">AI 源<strong>{{ settings?.default_ai_provider || '-' }}</strong><span>投研解释</span></div>
      </div>
    </section>

    <section class="panel span-12">
      <el-table :data="settings?.providers || []" v-loading="loading" height="360">
        <el-table-column prop="provider_name" label="数据源" width="160" />
        <el-table-column prop="provider_code" label="代码" width="120" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.configured ? 'success' : 'danger'">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="base_url" label="接口地址" min-width="230" />
        <el-table-column label="Token" width="160">
          <template #default="{ row }">{{ row.token_masked || '未配置' }}</template>
        </el-table-column>
        <el-table-column label="请求间隔" width="120">
          <template #default="{ row }">{{ row.request_interval_seconds == null ? '-' : `${row.request_interval_seconds}s` }}</template>
        </el-table-column>
        <el-table-column label="估算频率" width="120">
          <template #default="{ row }">{{ row.max_requests_per_minute ? `${row.max_requests_per_minute}/分钟` : '-' }}</template>
        </el-table-column>
        <el-table-column label="使用模块" min-width="260">
          <template #default="{ row }">
            <el-tag v-for="item in row.used_by" :key="item" class="tag-gap" type="info">{{ item }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel span-6" v-for="provider in settings?.providers || []" :key="provider.provider_code">
      <div class="panel-header">
        <h2>{{ provider.provider_name }}</h2>
        <el-tag :type="provider.configured ? 'success' : 'danger'">{{ provider.configured ? '已配置' : '未配置' }}</el-tag>
      </div>
      <div class="insight-list">
        <div class="insight-item">
          <span>配置方式</span>
          <p>{{ configHelp(provider.provider_code) }}</p>
        </div>
        <div class="insight-item">
          <span>说明</span>
          <ul>
            <li v-for="note in provider.notes" :key="note">{{ note }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel span-12">
      <h2>为什么不在前端填写 Token</h2>
      <p class="section-note">
        浏览器代码和网络请求都可能被用户或插件看到，Token 放前端会有泄漏风险。正式系统应在服务器环境变量或加密配置表中保存密钥，前端只负责显示“是否配置”和触发后端同步任务。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDataSourceSettings, type DataSourceSettings } from '../api/client'

const settings = ref<DataSourceSettings | null>(null)
const loading = ref(false)

onMounted(loadSettings)

async function loadSettings() {
  loading.value = true
  try {
    settings.value = await fetchDataSourceSettings()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取数据源配置失败')
  } finally {
    loading.value = false
  }
}

function statusText(status: string) {
  const map: Record<string, string> = {
    ready: '可用',
    missing_token: '缺少 Token',
  }
  return map[status] || status
}

function configHelp(providerCode: string) {
  if (providerCode === 'tushare') return '在服务器 .env.production 中配置 TUSHARE_TOKEN、TUSHARE_API_URL 和 TUSHARE_REQUEST_INTERVAL_SECONDS。'
  if (providerCode === 'deepseek') return '在服务器 .env.production 中配置 DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、DEEPSEEK_MODEL。'
  return '由后端统一读取配置，前端不保存密钥。'
}
</script>

<style scoped>
.tag-gap {
  margin: 2px 4px 2px 0;
}
</style>
