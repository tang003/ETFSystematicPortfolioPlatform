import { createRouter, createWebHistory } from 'vue-router'
import { fetchAuthStatus } from '../api/client'

const Login = () => import('../views/Login.vue')
const Dashboard = () => import('../views/Dashboard.vue')
const PortfolioWorkbench = () => import('../views/PortfolioWorkbench.vue')
const Workflow = () => import('../views/Workflow.vue')
const StrategyManagement = () => import('../views/StrategyManagement.vue')
const Assets = () => import('../views/Assets.vue')
const EtfScreener = () => import('../views/EtfScreener.vue')
const EtfCompare = () => import('../views/EtfCompare.vue')
const EtfDetail = () => import('../views/EtfDetail.vue')
const DataHealth = () => import('../views/DataHealth.vue')
const DataSourceManagement = () => import('../views/DataSourceManagement.vue')
const Factors = () => import('../views/Factors.vue')
const FactorResearch = () => import('../views/FactorResearch.vue')
const Portfolio = () => import('../views/Portfolio.vue')
const Holdings = () => import('../views/Holdings.vue')
const InvestmentPlans = () => import('../views/InvestmentPlans.vue')
const RiskRebalance = () => import('../views/RiskRebalance.vue')
const Backtest = () => import('../views/Backtest.vue')
const Reports = () => import('../views/Reports.vue')
const SystemStatus = () => import('../views/SystemStatus.vue')
const AgentAnalysis = () => import('../views/AgentAnalysis.vue')
const News = () => import('../views/News.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login, meta: { title: '登录', public: true } },
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: Dashboard, meta: { title: '总览' } },
    { path: '/portfolio-workbench', component: PortfolioWorkbench, meta: { title: '组合工作台' } },
    { path: '/workflow', component: Workflow, meta: { title: '全流程向导' } },
    { path: '/strategy-management', component: StrategyManagement, meta: { title: '策略管理' } },
    { path: '/assets', component: Assets, meta: { title: 'ETF 池' } },
    { path: '/etf-screener', component: EtfScreener, meta: { title: 'ETF 筛选' } },
    { path: '/etf-compare', component: EtfCompare, meta: { title: 'ETF 对比' } },
    { path: '/etf-detail/:symbol', component: EtfDetail, meta: { title: 'ETF 详情' } },
    { path: '/agent-analysis', component: AgentAnalysis, meta: { title: 'AI 投研委员会' } },
    { path: '/news', component: News, meta: { title: '新闻资讯' } },
    { path: '/data-health', component: DataHealth, meta: { title: '数据健康' } },
    { path: '/data-sources', component: DataSourceManagement, meta: { title: '数据源管理' } },
    { path: '/system-status', component: SystemStatus, meta: { title: '系统状态' } },
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
