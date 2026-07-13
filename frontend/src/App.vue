<template>
  <router-view v-if="$route.meta.public" />
  <el-container v-else class="shell">
    <el-aside width="244px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">ETF</div>
        <div>
          <div class="brand-title">系统化资产配置</div>
          <div class="brand-subtitle">ETF 控制台</div>
        </div>
      </div>
      <el-menu :default-active="$route.path" router class="nav">
        <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon><span>总览</span></el-menu-item>
        <el-menu-item index="/portfolio-workbench"><el-icon><Monitor /></el-icon><span>组合工作台</span></el-menu-item>
        <el-menu-item index="/workflow"><el-icon><Operation /></el-icon><span>全流程</span></el-menu-item>
        <el-menu-item index="/assets"><el-icon><Grid /></el-icon><span>ETF 池</span></el-menu-item>
        <el-menu-item index="/etf-compare"><el-icon><DataLine /></el-icon><span>ETF 对比</span></el-menu-item>
        <el-menu-item index="/data-health"><el-icon><CircleCheck /></el-icon><span>数据健康</span></el-menu-item>
        <el-menu-item index="/system-status"><el-icon><Setting /></el-icon><span>系统状态</span></el-menu-item>
        <el-menu-item index="/factors"><el-icon><TrendCharts /></el-icon><span>因子排名</span></el-menu-item>
        <el-menu-item index="/factor-research"><el-icon><DataAnalysis /></el-icon><span>因子研究</span></el-menu-item>
        <el-menu-item index="/portfolio"><el-icon><PieChart /></el-icon><span>目标组合</span></el-menu-item>
        <el-menu-item index="/holdings"><el-icon><Wallet /></el-icon><span>当前持仓</span></el-menu-item>
        <el-menu-item index="/investment-plans"><el-icon><Money /></el-icon><span>定投计划</span></el-menu-item>
        <el-menu-item index="/risk-rebalance"><el-icon><Warning /></el-icon><span>风控调仓</span></el-menu-item>
        <el-menu-item index="/backtest"><el-icon><Histogram /></el-icon><span>回测</span></el-menu-item>
        <el-menu-item index="/reports"><el-icon><Document /></el-icon><span>报告</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div>
          <h1>{{ $route.meta.title }}</h1>
          <p>ETF Systematic Portfolio Platform</p>
        </div>
        <div class="topbar-actions">
          <el-tag :type="healthOk ? 'success' : 'danger'" round>{{ healthOk ? 'API 正常' : 'API 异常' }}</el-tag>
          <el-button v-if="authEnabled" :icon="SwitchButton" circle title="退出登录" @click="handleLogout" />
        </div>
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CircleCheck, DataAnalysis, DataBoard, DataLine, Document, Grid, Histogram, Money, Monitor, Operation, PieChart, Setting, SwitchButton, TrendCharts, Wallet, Warning } from '@element-plus/icons-vue'
import { fetchAuthStatus, fetchHealth, logout } from './api/client'

const healthOk = ref(false)
const authEnabled = ref(false)
const router = useRouter()

onMounted(async () => {
  try {
    const [, authStatus] = await Promise.all([fetchHealth(), fetchAuthStatus()])
    healthOk.value = true
    authEnabled.value = authStatus.enabled
  } catch {
    healthOk.value = false
  }
})

async function handleLogout() {
  await logout()
  await router.replace('/login')
}
</script>
