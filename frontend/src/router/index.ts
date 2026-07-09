import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Workflow from '../views/Workflow.vue'
import Assets from '../views/Assets.vue'
import DataHealth from '../views/DataHealth.vue'
import Factors from '../views/Factors.vue'
import Portfolio from '../views/Portfolio.vue'
import RiskRebalance from '../views/RiskRebalance.vue'
import Backtest from '../views/Backtest.vue'
import Reports from '../views/Reports.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: Dashboard, meta: { title: '总览' } },
    { path: '/workflow', component: Workflow, meta: { title: '全流程向导' } },
    { path: '/assets', component: Assets, meta: { title: 'ETF 池' } },
    { path: '/data-health', component: DataHealth, meta: { title: '数据健康' } },
    { path: '/factors', component: Factors, meta: { title: '因子排名' } },
    { path: '/portfolio', component: Portfolio, meta: { title: '目标组合' } },
    { path: '/risk-rebalance', component: RiskRebalance, meta: { title: '风控调仓' } },
    { path: '/backtest', component: Backtest, meta: { title: '回测' } },
    { path: '/reports', component: Reports, meta: { title: '报告' } },
  ],
})

export default router
