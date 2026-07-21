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
        <el-menu-item v-for="item in visibleNavItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div>
          <h1>{{ $route.meta.title }}</h1>
          <p>ETF Systematic Portfolio Platform</p>
        </div>
        <div class="topbar-actions">
          <el-tag v-if="authEnabled" type="info" round>{{ roleLabel }}</el-tag>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  CircleCheck,
  DataAnalysis,
  DataBoard,
  DataLine,
  Document,
  Filter,
  Grid,
  Histogram,
  MagicStick,
  Money,
  Monitor,
  Operation,
  PieChart,
  Setting,
  SwitchButton,
  TrendCharts,
  User,
  Wallet,
  Warning,
} from '@element-plus/icons-vue'
import { fetchAuthStatus, fetchHealth, logout } from './api/client'

type Role = 'admin' | 'researcher' | 'viewer'
type NavItem = {
  path: string
  label: string
  icon: unknown
  roles?: Role[]
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: '总览', icon: DataBoard },
  { path: '/portfolio-workbench', label: '组合工作台', icon: Monitor },
  { path: '/workflow', label: '全流程', icon: Operation, roles: ['admin'] },
  { path: '/strategy-management', label: '策略管理', icon: TrendCharts, roles: ['admin'] },
  { path: '/assets', label: 'ETF 池', icon: Grid },
  { path: '/etf-screener', label: 'ETF 筛选', icon: Filter },
  { path: '/etf-compare', label: 'ETF 对比', icon: DataLine },
  { path: '/agent-analysis', label: 'AI 投研', icon: MagicStick },
  { path: '/news', label: '新闻资讯', icon: Document },
  { path: '/data-health', label: '数据健康', icon: CircleCheck, roles: ['admin'] },
  { path: '/data-sources', label: '数据源管理', icon: Setting, roles: ['admin'] },
  { path: '/system-status', label: '系统状态', icon: Setting, roles: ['admin'] },
  { path: '/audit-logs', label: '操作审计', icon: Document, roles: ['admin'] },
  { path: '/users', label: '用户管理', icon: User, roles: ['admin'] },
  { path: '/factors', label: '因子排名', icon: TrendCharts },
  { path: '/factor-research', label: '因子研究', icon: DataAnalysis, roles: ['admin', 'researcher'] },
  { path: '/portfolio', label: '目标组合', icon: PieChart },
  { path: '/holdings', label: '当前持仓', icon: Wallet, roles: ['admin', 'researcher'] },
  { path: '/investment-plans', label: '定投计划', icon: Money, roles: ['admin', 'researcher'] },
  { path: '/risk-rebalance', label: '风控调仓', icon: Warning, roles: ['admin', 'researcher'] },
  { path: '/backtest', label: '回测', icon: Histogram, roles: ['admin', 'researcher'] },
  { path: '/reports', label: '报告', icon: Document },
]

const healthOk = ref(false)
const authEnabled = ref(false)
const currentRole = ref<Role>('viewer')
const router = useRouter()

const visibleNavItems = computed(() =>
  navItems.filter((item) => !item.roles || item.roles.includes(currentRole.value)),
)

const roleLabel = computed(() => {
  const map: Record<Role, string> = {
    admin: '管理员',
    researcher: '研究员',
    viewer: '观察者',
  }
  return map[currentRole.value] || currentRole.value
})

onMounted(async () => {
  try {
    const [, authStatus] = await Promise.all([fetchHealth(), fetchAuthStatus()])
    healthOk.value = true
    authEnabled.value = authStatus.enabled
    currentRole.value = normalizeRole(authStatus.role)
  } catch {
    healthOk.value = false
  }
})

async function handleLogout() {
  await logout()
  await router.replace('/login')
}

function normalizeRole(role: string | null | undefined): Role {
  if (role === 'admin' || role === 'researcher') return role
  return 'viewer'
}
</script>
