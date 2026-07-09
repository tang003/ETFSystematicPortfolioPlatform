<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-12">
      <div class="panel-header">
        <h2>生成报告</h2>
        <el-button type="primary" :loading="actionLoading" @click="runReportGeneration">生成月度报告</el-button>
      </div>
      <el-form class="action-form" label-width="92px">
        <el-form-item label="运行 ID">
          <el-input-number v-model="runId" :min="1" />
          <span class="form-note">可留用默认值；后端也支持不指定 run_id。</span>
        </el-form-item>
        <el-form-item label="报告日期">
          <el-date-picker v-model="reportDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
    </section>
    <section class="panel span-4">
      <h2>报告列表</h2>
      <el-table :data="reports" height="620" highlight-current-row @current-change="selectReport">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="report_date" label="日期" width="120" />
        <el-table-column prop="title" label="标题" min-width="220" />
      </el-table>
    </section>
    <section class="panel span-8">
      <h2>{{ selected?.title ?? '报告详情' }}</h2>
      <div class="markdown" v-html="renderedMarkdown"></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchReport, fetchReports, generateMonthlyReport, type Report } from '../api/client'

const reports = ref<Report[]>([])
const selected = ref<Report>()
const loading = ref(true)
const actionLoading = ref(false)
const runId = ref(1)
const reportDate = ref(new Date().toISOString().slice(0, 10))

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    reports.value = await fetchReports()
    if (reports.value[0]) selected.value = await fetchReport(reports.value[0].id)
  } finally {
    loading.value = false
  }
}

async function selectReport(row: Report | undefined) {
  if (row) selected.value = await fetchReport(row.id)
}

const renderedMarkdown = computed(() => markdownToHtml(selected.value?.content_markdown ?? ''))

function markdownToHtml(markdown: string) {
  return markdown
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^- (.*)$/gm, '<p>$1</p>')
    .replace(/\n/g, '<br />')
}

async function runReportGeneration() {
  actionLoading.value = true
  try {
    const result = await generateMonthlyReport({ run_id: runId.value, report_date: reportDate.value })
    ElMessage.success(`报告生成完成，report_id=${String(result.id ?? '-')}`)
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '报告生成失败')
  } finally {
    actionLoading.value = false
  }
}
</script>
