<template>
  <el-container class="shell">
    <el-aside width="244px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">ETF</div>
        <div>
          <div class="brand-title">Portfolio Platform</div>
          <div class="brand-subtitle">Systematic Console</div>
        </div>
      </div>
      <el-menu :default-active="$route.path" router class="nav">
        <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon><span>Dashboard</span></el-menu-item>
        <el-menu-item index="/assets"><el-icon><Grid /></el-icon><span>ETF Pool</span></el-menu-item>
        <el-menu-item index="/data-health"><el-icon><CircleCheck /></el-icon><span>Data Health</span></el-menu-item>
        <el-menu-item index="/factors"><el-icon><TrendCharts /></el-icon><span>Factors</span></el-menu-item>
        <el-menu-item index="/portfolio"><el-icon><PieChart /></el-icon><span>Portfolio</span></el-menu-item>
        <el-menu-item index="/risk-rebalance"><el-icon><Warning /></el-icon><span>Risk & Orders</span></el-menu-item>
        <el-menu-item index="/backtest"><el-icon><Histogram /></el-icon><span>Backtest</span></el-menu-item>
        <el-menu-item index="/reports"><el-icon><Document /></el-icon><span>Reports</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div>
          <h1>{{ $route.meta.title }}</h1>
          <p>ETF Systematic Portfolio Platform</p>
        </div>
        <el-tag :type="healthOk ? 'success' : 'danger'" round>{{ healthOk ? 'API Online' : 'API Offline' }}</el-tag>
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CircleCheck, DataBoard, Document, Grid, Histogram, PieChart, TrendCharts, Warning } from '@element-plus/icons-vue'
import { fetchHealth } from './api/client'

const healthOk = ref(false)

onMounted(async () => {
  try {
    await fetchHealth()
    healthOk.value = true
  } catch {
    healthOk.value = false
  }
})
</script>

