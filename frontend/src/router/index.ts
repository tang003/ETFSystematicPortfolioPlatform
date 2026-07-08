import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
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
    { path: '/dashboard', component: Dashboard, meta: { title: 'Dashboard' } },
    { path: '/assets', component: Assets, meta: { title: 'ETF Pool' } },
    { path: '/data-health', component: DataHealth, meta: { title: 'Data Health' } },
    { path: '/factors', component: Factors, meta: { title: 'Factor Ranking' } },
    { path: '/portfolio', component: Portfolio, meta: { title: 'Target Portfolio' } },
    { path: '/risk-rebalance', component: RiskRebalance, meta: { title: 'Risk & Rebalance' } },
    { path: '/backtest', component: Backtest, meta: { title: 'Backtest' } },
    { path: '/reports', component: Reports, meta: { title: 'Reports' } },
  ],
})

export default router

