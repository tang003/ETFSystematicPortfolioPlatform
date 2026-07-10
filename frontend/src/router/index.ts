import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import PortfolioWorkbench from '../views/PortfolioWorkbench.vue'
import Workflow from '../views/Workflow.vue'
import Assets from '../views/Assets.vue'
import DataHealth from '../views/DataHealth.vue'
import Factors from '../views/Factors.vue'
import FactorResearch from '../views/FactorResearch.vue'
import Portfolio from '../views/Portfolio.vue'
import Holdings from '../views/Holdings.vue'
import InvestmentPlans from '../views/InvestmentPlans.vue'
import RiskRebalance from '../views/RiskRebalance.vue'
import Backtest from '../views/Backtest.vue'
import Reports from '../views/Reports.vue'
import Login from '../views/Login.vue'
import { fetchAuthStatus } from '../api/client'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login, meta: { title: '登录', public: true } },
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: Dashboard, meta: { title: '总览' } },
    { path: '/portfolio-workbench', component: PortfolioWorkbench, meta: { title: '组合工作台' } },
    { path: '/workflow', component: Workflow, meta: { title: '全流程向导' } },
    { path: '/assets', component: Assets, meta: { title: 'ETF 池' } },
    { path: '/data-health', component: DataHealth, meta: { title: '数据健康' } },
    { path: '/factors', component: Factors, meta: { title: '因子排名' } },
    { path: '/factor-research', component: FactorResearch, meta: { title: '因子研究' } },
    { path: '/portfolio', component: Portfolio, meta: { title: '目标组合' } },
    { path: '/holdings', component: Holdings, meta: { title: '当前持仓' } },
    { path: '/investment-plans', component: InvestmentPlans, meta: { title: '定投计划' } },
    { path: '/risk-rebalance', component: RiskRebalance, meta: { title: '风控调仓' } },
    { path: '/backtest', component: Backtest, meta: { title: '回测' } },
    { path: '/reports', component: Reports, meta: { title: '报告' } },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  try {
    const status = await fetchAuthStatus()
    if (status.authenticated) return true
  } catch {
    // The login page will show the API connection error.
  }
  return { path: '/login', query: { redirect: to.fullPath } }
})

export default router
