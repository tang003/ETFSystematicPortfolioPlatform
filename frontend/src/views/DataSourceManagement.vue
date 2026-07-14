<template>
  <div class="page-grid">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>数据源管理</h2>
          <p class="section-note">统一查看和维护行情、基金资料、交易日历和 AI 接口。密钥只写入后端，前端不会回显明文。</p>
        </div>
        <div class="task-tags">
          <el-button :loading="loading" @click="loadSettings">刷新状态</el-button>
          <el-button type="primary" @click="openCreate">新增数据源</el-button>
        </div>
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
        <el-table-column prop="provider_type" label="类型" width="100" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.configured ? 'success' : 'danger'">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适配" width="120">
          <template #default="{ row }">
            <el-tag :type="row.adapter_status === 'runtime_supported' ? 'success' : 'warning'">{{ adapterText(row.adapter_status) }}</el-tag>
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
        <el-table-column label="限额" width="140">
          <template #default="{ row }">{{ quotaText(row) }}</template>
        </el-table-column>
        <el-table-column label="使用模块" min-width="260">
          <template #default="{ row }">
            <el-tag v-for="item in row.used_by" :key="item" class="tag-gap" type="info">{{ item }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link :type="row.enabled ? 'warning' : 'success'" @click="toggle(row)">
              {{ row.enabled ? '停用' : '启用' }}
            </el-button>
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
        浏览器代码和网络请求都可能被用户或插件看到，Token 放前端会有泄漏风险。本页面只允许把密钥提交给后端保存，之后只显示脱敏结果。新增数据源默认是“仅登记”，要真正用于行情同步，还需要后端适配字段口径、分页、限频和错误处理。
      </p>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingCode ? '编辑数据源' : '新增数据源'" width="760px">
      <el-form label-width="118px">
        <el-form-item label="数据源代码">
          <el-input v-model="form.provider_code" :disabled="Boolean(editingCode)" placeholder="例如 my_tushare_proxy" />
        </el-form-item>
        <el-form-item label="数据源名称">
          <el-input v-model="form.provider_name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.provider_type">
            <el-option label="行情/资料" value="market" />
            <el-option label="AI" value="ai" />
            <el-option label="新闻/资讯" value="news" />
            <el-option label="券商/交易" value="broker" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="form.base_url" placeholder="https://api.example.com" />
        </el-form-item>
        <el-form-item label="鉴权方式">
          <el-select v-model="form.auth_type">
            <el-option label="Token" value="token" />
            <el-option label="Bearer" value="bearer" />
            <el-option label="无需鉴权" value="none" />
          </el-select>
        </el-form-item>
        <el-form-item label="写入新密钥">
          <el-input v-model="secretValue" type="password" show-password placeholder="留空表示不修改已有密钥" />
        </el-form-item>
        <el-form-item v-if="editingCode" label="清空密钥">
          <el-switch v-model="clearSecret" />
        </el-form-item>
        <el-form-item label="请求间隔">
          <el-input-number v-model="form.request_interval_seconds" :min="0" :max="60" :step="0.1" />
          <span class="form-note">单位秒；Tushare 合租 Token 建议保守设置。</span>
        </el-form-item>
        <el-form-item label="每分钟限额">
          <el-input-number v-model="form.quota_per_minute" :min="0" :max="10000" />
        </el-form-item>
        <el-form-item label="每日限额">
          <el-input-number v-model="form.quota_per_day" :min="0" :max="10000000" />
        </el-form-item>
        <el-form-item label="支持用途">
          <el-select v-model="form.supported_usages" multiple>
            <el-option label="交易日历" value="calendar" />
            <el-option label="ETF 日线行情" value="market_daily" />
            <el-option label="ETF 基础池" value="asset_universe" />
            <el-option label="ETF 主资料" value="asset_profile" />
            <el-option label="AI 投研" value="ai_research" />
            <el-option label="报告增强" value="report_enhancement" />
            <el-option label="新闻资讯" value="news" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务适配">
          <el-select v-model="form.adapter_status">
            <el-option label="已接入运行时" value="runtime_supported" />
            <el-option label="仅登记配置" value="metadata_only" />
            <el-option label="开发中" value="planned" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="notesText" type="textarea" :rows="3" placeholder="每行一条说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createDataSource, fetchDataSourceSettings, updateDataSource, type DataSourceProvider, type DataSourceSettings } from '../api/client'

const settings = ref<DataSourceSettings | null>(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingCode = ref('')
const secretValue = ref('')
const clearSecret = ref(false)
const notesText = ref('')
const form = reactive({
  provider_code: '',
  provider_name: '',
  provider_type: 'market',
  enabled: true,
  base_url: '',
  auth_type: 'token',
  request_interval_seconds: null as number | null,
  quota_per_minute: null as number | null,
  quota_per_day: null as number | null,
  supported_usages: [] as string[],
  adapter_status: 'metadata_only',
})

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
    disabled: '已停用',
    metadata_only: '仅登记',
  }
  return map[status] || status
}

function adapterText(status: string) {
  const map: Record<string, string> = {
    runtime_supported: '已接入',
    metadata_only: '仅登记',
    planned: '开发中',
  }
  return map[status] || status
}

function configHelp(providerCode: string) {
  if (providerCode === 'tushare') return '可在本页调整 Tushare API 地址、Token 和限频；数据库配置优先于服务器环境变量。'
  if (providerCode === 'deepseek') return '可在本页调整 DeepSeek API 地址和 Key；模型名称仍由服务器环境变量控制。'
  return '新增数据源会先进入配置中心；要用于行情同步，需要后端开发适配器。'
}

function quotaText(row: DataSourceProvider) {
  const minute = row.quota_per_minute ? `${row.quota_per_minute}/分钟` : '-'
  const day = row.quota_per_day ? `${row.quota_per_day}/日` : '-'
  return `${minute} / ${day}`
}

function openCreate() {
  editingCode.value = ''
  Object.assign(form, {
    provider_code: '',
    provider_name: '',
    provider_type: 'market',
    enabled: true,
    base_url: '',
    auth_type: 'token',
    request_interval_seconds: null,
    quota_per_minute: null,
    quota_per_day: null,
    supported_usages: [],
    adapter_status: 'metadata_only',
  })
  secretValue.value = ''
  clearSecret.value = false
  notesText.value = ''
  dialogVisible.value = true
}

function openEdit(row: DataSourceProvider) {
  editingCode.value = row.provider_code
  Object.assign(form, {
    provider_code: row.provider_code,
    provider_name: row.provider_name,
    provider_type: row.provider_type,
    enabled: row.enabled,
    base_url: row.base_url || '',
    auth_type: row.auth_type,
    request_interval_seconds: row.request_interval_seconds,
    quota_per_minute: row.quota_per_minute,
    quota_per_day: row.quota_per_day,
    supported_usages: [...row.supported_usages],
    adapter_status: row.adapter_status,
  })
  secretValue.value = ''
  clearSecret.value = false
  notesText.value = row.notes.join('\n')
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = {
      provider_name: form.provider_name,
      provider_type: form.provider_type,
      enabled: form.enabled,
      base_url: form.base_url || null,
      auth_type: form.auth_type,
      secret_value: secretValue.value || null,
      clear_secret: clearSecret.value,
      request_interval_seconds: form.request_interval_seconds,
      quota_per_minute: form.quota_per_minute,
      quota_per_day: form.quota_per_day,
      supported_usages: form.supported_usages,
      adapter_status: form.adapter_status,
      notes: notesText.value.split('\n').map((item) => item.trim()).filter(Boolean),
    }
    if (editingCode.value) {
      await updateDataSource(editingCode.value, payload)
    } else {
      await createDataSource({ provider_code: form.provider_code, ...payload })
    }
    ElMessage.success('数据源配置已保存')
    dialogVisible.value = false
    await loadSettings()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存数据源失败')
  } finally {
    saving.value = false
  }
}

async function toggle(row: DataSourceProvider) {
  await updateDataSource(row.provider_code, { enabled: !row.enabled })
  ElMessage.success(row.enabled ? '数据源已停用' : '数据源已启用')
  await loadSettings()
}
</script>

<style scoped>
.tag-gap {
  margin: 2px 4px 2px 0;
}
</style>
