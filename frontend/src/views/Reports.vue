<template>
  <div class="page-grid" v-loading="loading">
    <section class="panel span-4">
      <h2>Reports</h2>
      <el-table :data="reports" height="620" highlight-current-row @current-change="selectReport">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="report_date" label="Date" width="120" />
        <el-table-column prop="title" label="Title" min-width="220" />
      </el-table>
    </section>
    <section class="panel span-8">
      <h2>{{ selected?.title ?? 'Report Detail' }}</h2>
      <div class="markdown" v-html="renderedMarkdown"></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchReport, fetchReports, type Report } from '../api/client'

const reports = ref<Report[]>([])
const selected = ref<Report>()
const loading = ref(true)

onMounted(async () => {
  try {
    reports.value = await fetchReports()
    if (reports.value[0]) selected.value = await fetchReport(reports.value[0].id)
  } finally {
    loading.value = false
  }
})

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
</script>

