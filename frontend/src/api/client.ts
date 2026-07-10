import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 20000,
  withCredentials: true,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = String(error?.config?.url || '')
    if (error?.response?.status === 401 && !requestUrl.includes('/api/auth/login') && window.location.pathname !== '/login') {
      const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
      window.location.assign(`/login?redirect=${redirect}`)
    }
    return Promise.reject(error)
  },
)

export interface AuthStatus {
  enabled: boolean
  configured: boolean
  authenticated: boolean
  username: string | null
}

export interface Asset {
  symbol: string
  name: string
  exchange: string | null
  asset_class: string
  asset_region: string | null
  currency?: string
  enabled: boolean
  risk_level: number
  is_cross_border: boolean
  description?: string | null
}

export interface AssetUpsertItem {
  symbol: string
  name: string
  exchange?: string | null
  asset_class?: string
  asset_region?: string | null
  currency?: string
  is_cross_border?: boolean
  is_leveraged?: boolean
  is_inverse?: boolean
  enabled?: boolean
  risk_level?: number
  description?: string | null
}

export interface DataQualityStatus {
  total_logs: number
  error_logs: number
  warning_logs: number
  latest_created_at: string | null
  status: string
}

export interface DataQualityLog {
  symbol: string | null
  trade_date: string | null
  check_type: string
  status: string
  message: string | null
  severity: string
  created_at: string
}

export interface Factor {
  symbol: string
  trade_date: string
  trend_score: string | null
  momentum_score: string | null
  volatility_score: string | null
  drawdown_score: string | null
  liquidity_score: string | null
  premium_score: string | null
  alpha_score: string | null
}

export interface FactorIcMetric {
  factor_name: string
  observations: number
  mean_ic: string | null
  mean_rank_ic: string | null
  positive_ic_ratio: string | null
  effective: boolean
}

export interface FactorCorrelationMetric {
  factor_x: string
  factor_y: string
  correlation: string | null
}

export interface FactorQuantileReturnMetric {
  factor_name: string
  quantile: number
  mean_forward_return: string | null
  observations: number
}

export interface FactorResearchResult {
  start_date: string | null
  end_date: string | null
  forward_days: number
  quantiles: number
  factor_count: number
  sample_count: number
  ic_metrics: FactorIcMetric[]
  correlations: FactorCorrelationMetric[]
  quantile_returns: FactorQuantileReturnMetric[]
}

export interface TargetPortfolio {
  run_id: number | null
  portfolio_date: string
  symbol: string
  raw_target_weight: string | null
  final_target_weight: string | null
  asset_class: string | null
  reason: string | null
}

export interface PortfolioPosition {
  position_date: string
  symbol: string
  position_name: string | null
  asset_type: string | null
  quantity: string | null
  current_price: string | null
  cost_price: string | null
  market_value: string | null
  weight: string | null
  cost_basis: string | null
  unrealized_pnl: string | null
  unrealized_pnl_rate: string | null
  created_at: string
}

export interface PositionResolveResult {
  symbol: string
  position_name: string | null
  asset_type: string | null
  current_price: string | null
  price_date: string | null
  resolved: boolean
  message: string | null
}

export interface HoldingAnalysis {
  run_id: number | null
  analysis_date: string
  symbol: string
  current_weight: string | null
  target_weight: string | null
  weight_diff: string | null
  action_suggestion: string
  alpha_score: string | null
  reason: string | null
  created_at: string
}

export interface InvestmentPlan {
  id: number
  plan_name: string
  run_id: number | null
  start_date: string
  months: number
  monthly_amount: string
  total_budget: string
  target_annual_return: string | null
  investment_mode: string
  status: string
  note: string | null
  created_at: string
}

export interface InvestmentPlanSuggestion {
  plan_id: number
  run_id: number | null
  suggestion_date: string
  period_no: number
  symbol: string
  target_weight: string | null
  current_weight: string | null
  gap_weight: string | null
  suggested_amount: string
  action_suggestion: string
  reason: string | null
  created_at: string
}

export interface PortfolioExposure {
  dimension: string
  name: string
  current_weight: string
  target_weight: string
  diff_weight: string
}

export interface PortfolioReadiness {
  enabled_etf_count: number
  position_count: number
  target_count: number
  latest_market_date: string | null
  latest_factor_date: string | null
  missing_market_count: number
  high_risk_target_weight: string
  cross_border_target_weight: string
  max_single_target_weight: string
  status: string
  messages: string[]
}

export interface PortfolioXray {
  exposures: PortfolioExposure[]
  readiness: PortfolioReadiness
}

export interface RiskResult {
  run_id: number | null
  check_date: string
  rule_code: string
  status: string
  message: string | null
  before_value: string | null
  after_value: string | null
}

export interface RebalanceOrder {
  run_id: number | null
  order_date: string
  symbol: string
  action: string
  current_weight: string | null
  target_weight: string | null
  weight_diff: string | null
  estimated_amount: string | null
  reason: string | null
  status: string
}

export interface BacktestRun {
  id: number
  strategy_code: string
  name: string | null
  start_date: string | null
  end_date: string | null
  status: string
}

export interface BacktestCurvePoint {
  trade_date: string
  total_equity: string | null
  drawdown: string | null
  daily_return: string | null
}

export interface BacktestMetric {
  metric_name: string
  metric_value: string | null
  metric_unit: string | null
}

export interface BacktestTrade {
  trade_date: string
  symbol: string
  action: string
  price: string | null
  quantity: string | null
  amount: string | null
  fee: string | null
  slippage: string | null
  reason: string | null
}

export interface Report {
  id: number
  run_id: number | null
  report_date: string
  report_type: string
  title: string | null
  content_markdown: string | null
  status: string
  created_at: string
}

export interface RunSummary {
  status: string
  [key: string]: unknown
}

export interface WorkflowTaskStep {
  id: number
  task_id: number
  step_key: string
  step_name: string
  sort_order: number
  status: string
  message: string | null
  result_payload: Record<string, unknown> | null
  started_at: string | null
  finished_at: string | null
}

export interface WorkflowTask {
  id: number
  task_type: string
  status: string
  current_step: string | null
  request_payload: Record<string, unknown>
  result_payload: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  steps: WorkflowTaskStep[]
}

export const fetchHealth = async () => (await api.get('/health')).data
export const fetchAuthStatus = async () => (await api.get<AuthStatus>('/api/auth/status')).data
export const login = async (payload: { username: string; password: string }) =>
  (await api.post<AuthStatus>('/api/auth/login', payload)).data
export const logout = async () => (await api.post<AuthStatus>('/api/auth/logout')).data
export const fetchAssets = async () => (await api.get<Asset[]>('/api/assets')).data
export const batchUpsertAssets = async (payload: { items: AssetUpsertItem[] }) =>
  (await api.post<{ total: number; inserted_or_updated: number }>('/api/assets/batch-upsert', payload)).data
export const updateAsset = async (symbol: string, payload: { enabled?: boolean; risk_level?: number; description?: string | null }) =>
  (await api.patch<Asset>(`/api/assets/${symbol}`, payload)).data
export const fetchDataQualityStatus = async () => (await api.get<DataQualityStatus>('/api/data-quality/status')).data
export const fetchDataQualityLogs = async () => (await api.get<DataQualityLog[]>('/api/data-quality/logs?limit=50')).data
export const fetchFactorRanking = async () => (await api.get<Factor[]>('/api/factors/ranking?limit=50')).data
export const fetchTargetPortfolio = async () => (await api.get<TargetPortfolio[]>('/api/portfolio/target')).data
export const fetchPositions = async () => (await api.get<PortfolioPosition[]>('/api/portfolio/positions')).data
export const fetchPortfolioXray = async () => (await api.get<PortfolioXray>('/api/portfolio/xray')).data
export const resolvePositionSymbols = async (symbols: string[]) =>
  (await api.post<PositionResolveResult[]>('/api/portfolio/positions/resolve', { symbols })).data
export const savePositionSnapshot = async (payload: {
  position_date: string
  positions: Array<{
    symbol: string
    position_name?: string
    asset_type?: string
    quantity?: number
    current_price?: number
    cost_price?: number
    market_value?: number
    cost_basis?: number
  }>
}) =>
  (await api.post<PortfolioPosition[]>('/api/portfolio/positions', payload)).data
export const analyzeHoldings = async (payload: { run_id?: number; analysis_date?: string }) =>
  (await api.post<HoldingAnalysis[]>('/api/portfolio/holdings/analyze', payload)).data
export const fetchHoldingAnalysis = async () => (await api.get<HoldingAnalysis[]>('/api/portfolio/holdings/analysis')).data
export const createInvestmentPlan = async (payload: {
  plan_name: string
  run_id?: number
  start_date: string
  months: number
  monthly_amount?: number
  total_budget?: number
  target_annual_return?: number
  investment_mode?: string
  note?: string
}) =>
  (await api.post<InvestmentPlan>('/api/portfolio/investment-plans', payload)).data
export const fetchInvestmentPlans = async () => (await api.get<InvestmentPlan[]>('/api/portfolio/investment-plans')).data
export const analyzeInvestmentPlan = async (planId: number, payload: { period_no: number; suggestion_date?: string }) =>
  (await api.post<InvestmentPlanSuggestion[]>(`/api/portfolio/investment-plans/${planId}/analyze`, payload)).data
export const fetchInvestmentPlanSuggestions = async (planId: number) =>
  (await api.get<InvestmentPlanSuggestion[]>(`/api/portfolio/investment-plans/${planId}/suggestions`)).data
export const fetchRiskResults = async () => (await api.get<RiskResult[]>('/api/risk/results?limit=50')).data
export const fetchRebalanceOrders = async () => (await api.get<RebalanceOrder[]>('/api/rebalance/orders?limit=50')).data
export const fetchBacktestRuns = async () => (await api.get<BacktestRun[]>('/api/backtest/runs?limit=20')).data
export const fetchBacktestCurve = async (id: number) => (await api.get<BacktestCurvePoint[]>(`/api/backtest/${id}/equity-curve`)).data
export const fetchBacktestMetrics = async (id: number) => (await api.get<BacktestMetric[]>(`/api/backtest/${id}/metrics`)).data
export const fetchBacktestTrades = async (id: number) => (await api.get<BacktestTrade[]>(`/api/backtest/${id}/trades`)).data
export const fetchReports = async () => (await api.get<Report[]>('/api/reports?limit=20')).data
export const fetchReport = async (id: number) => (await api.get<Report>(`/api/reports/${id}`)).data
export const syncCalendar = async (payload: { start_date: string; end_date: string; market?: string; source?: string; incremental?: boolean }) =>
  (await api.post<RunSummary>('/api/calendar/sync', payload)).data
export const syncMarket = async (payload: {
  symbols?: string[]
  start_date?: string
  end_date?: string
  source?: string
  incremental?: boolean
  max_symbols?: number
  clean_after_sync?: boolean
  request_interval_seconds?: number
}) =>
  (await api.post<RunSummary>('/api/market/sync', payload)).data
export const checkDataQuality = async (payload: { symbols: string[]; start_date: string; end_date: string }) =>
  (await api.post<RunSummary[]>('/api/data-quality/check', payload)).data
export const calculateFactors = async (payload: { symbols?: string[]; start_date?: string; end_date?: string }) =>
  (await api.post<RunSummary>('/api/factors/calculate', payload)).data
export const researchFactors = async (payload: { start_date?: string; end_date?: string; forward_days: number; quantiles: number }) =>
  (await api.post<FactorResearchResult>('/api/factors/research', payload)).data
export const runStrategy = async (payload: { strategy_code: string; run_date?: string; run_type?: string }) =>
  (await api.post<RunSummary>('/api/strategies/run', payload)).data
export const checkRisk = async (payload: { run_id: number }) =>
  (await api.post<RunSummary>('/api/risk/check', payload)).data
export const generateRebalanceOrders = async (payload: { run_id: number; portfolio_value?: number }) =>
  (await api.post<RunSummary>('/api/rebalance/generate', payload)).data
export const runBacktest = async (payload: {
  strategy_code: string
  name?: string
  symbols?: string[]
  start_date: string
  end_date: string
  initial_cash?: number
  monthly_contribution?: number
  fee_rate?: number
  slippage_rate?: number
}) => (await api.post<RunSummary>('/api/backtest/run', payload)).data
export const generateMonthlyReport = async (payload: { run_id?: number; report_date?: string }) =>
  (await api.post<RunSummary>('/api/reports/monthly', payload)).data
export const startWorkflowTask = async (payload: {
  symbols?: string[]
  start_date: string
  end_date: string
  max_symbols?: number
  calendar_source?: string
  market_source?: string
  incremental_sync?: boolean
  request_interval_seconds?: number
  strict_data_validation?: boolean
  minimum_history_bars?: number
  strategy_code: string
  portfolio_value?: number
  generate_report?: boolean
}) => (await api.post<{ task_id: number; status: string }>('/api/workflows/run', payload)).data
export const fetchWorkflowTask = async (taskId: number) =>
  (await api.get<WorkflowTask>(`/api/workflows/${taskId}`)).data
export const fetchWorkflowTasks = async () =>
  (await api.get<WorkflowTask[]>('/api/workflows?limit=20')).data
export const cancelWorkflowTask = async (taskId: number) =>
  (await api.post<WorkflowTask>(`/api/workflows/${taskId}/cancel`)).data
export const retryFailedWorkflowTask = async (taskId: number) =>
  (await api.post<{ task_id: number; status: string }>(`/api/workflows/${taskId}/retry-failed`)).data
