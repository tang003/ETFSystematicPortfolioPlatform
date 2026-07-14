<template>
  <div class="page-grid">
    <section class="panel span-12">
      <div class="panel-header">
        <div>
          <h2>新闻资讯</h2>
          <p class="section-note">低频同步财经新闻到本地数据库，用关键词和 ETF 主资料做关联；外部接口不由前端直接请求。</p>
        </div>
        <div class="task-tags">
          <el-button :loading="loading" @click="loadNews">刷新列表</el-button>
          <el-button type="primary" :loading="syncing" @click="syncLatest">同步最新新闻</el-button>
        </div>
      </div>
      <el-form class="filter-form" :inline="true">
        <el-form-item label="关键词">
          <el-input v-model="q" clearable placeholder="例如 黄金、标普、半导体" @keyup.enter="loadNews" />
        </el-form-item>
        <el-form-item label="ETF 代码">
          <el-input v-model="symbol" clearable placeholder="例如 513500" @keyup.enter="loadNews" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="limit" :min="10" :max="200" :step="10" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadNews">查询</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="panel span-8">
      <el-table :data="articles" v-loading="loading" height="620">
        <el-table-column label="新闻" min-width="360">
          <template #default="{ row }">
            <div class="news-title">
              <a v-if="row.url" :href="row.url" target="_blank" rel="noreferrer">{{ row.title }}</a>
              <span v-else>{{ row.title }}</span>
            </div>
            <div class="news-meta">
              <span>{{ row.source_name || row.source }}</span>
              <span>{{ row.publish_time || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="关联 ETF" min-width="170">
          <template #default="{ row }">
            <el-tag v-for="item in row.related_symbols" :key="item" class="tag-gap" type="success">{{ item }}</el-tag>
            <span v-if="!row.related_symbols.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="190">
          <template #default="{ row }">
            <el-tag v-for="item in row.keywords" :key="item" class="tag-gap" type="info">{{ item }}</el-tag>
            <el-tag v-for="item in row.related_asset_class" :key="item" class="tag-gap" type="warning">{{ assetClassText(item) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="impact_level" label="影响" width="90" />
      </el-table>
    </section>

    <section class="panel span-4">
      <h2>同步策略</h2>
      <div class="insight-list">
        <div class="insight-item">
          <span>接口</span>
          <p>当前使用数据源管理中的 `juhe_finance_news`，每次最多同步 50 条。</p>
        </div>
        <div class="insight-item">
          <span>额度</span>
          <p>低配 50 次/天足够测试。建议每天 6-12 次，不要用户每次打开页面就请求外部接口。</p>
        </div>
        <div class="insight-item">
          <span>下一步</span>
          <p>后续可加入定时同步、AI 摘要、情绪分数，并在 ETF 详情页显示相关新闻。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchNews, syncNews, type NewsArticle } from '../api/client'

const articles = ref<NewsArticle[]>([])
const loading = ref(false)
const syncing = ref(false)
const q = ref('')
const symbol = ref('')
const limit = ref(50)

onMounted(loadNews)

async function loadNews() {
  loading.value = true
  try {
    articles.value = await fetchNews({
      q: q.value || undefined,
      symbol: symbol.value || undefined,
      limit: limit.value,
    })
  } finally {
    loading.value = false
  }
}

async function syncLatest() {
  syncing.value = true
  try {
    const result = await syncNews({ source: 'juhe_finance_news', num: 50, page: 1 })
    ElMessage.success(`同步完成：新增 ${String(result.inserted ?? 0)}，更新 ${String(result.updated ?? 0)}`)
    await loadNews()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同步新闻失败')
  } finally {
    syncing.value = false
  }
}

function assetClassText(value: string) {
  const map: Record<string, string> = {
    equity: '权益',
    bond: '债券',
    gold: '黄金',
    commodity: '商品',
  }
  return map[value] || value
}
</script>

<style scoped>
.filter-form {
  margin-top: 14px;
}

.news-title {
  font-weight: 700;
  line-height: 1.5;
}

.news-title a {
  color: #12365f;
  text-decoration: none;
}

.news-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  color: #8390a3;
  font-size: 12px;
}

.tag-gap {
  margin: 2px 4px 2px 0;
}
</style>
