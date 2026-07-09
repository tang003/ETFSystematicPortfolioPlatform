import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 20000,
})

export interface Asset {
  symbol: string
  name: string
  exchange: string | null
  asset_class: string
  asset_region: string | null
  enabled: boolean
  risk_level: number
  is_cross_border: boolean
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

export interface TargetPortfolio {
  run_id: number | null
  portfolio_date: string
  symbol: string
  raw_target_weight: string | null
  final_target_weight: string | null
  asset_class: string | null
  reason: string | null
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
export const fetchAssets = async () => (await api.get<Asset[]>('/api/assets')).data
export const fetchDataQualityStatus = async () => (await api.get<DataQualityStatus>('/api/data-quality/status')).data
export const fetchDataQualityLogs = async () => (await api.get<DataQualityLog[]>('/api/data-quality/logs?limit=50')).data
export const fetchFactorRanking = async () => (await api.get<Factor[]>('/api/factors/ranking?limit=50')).data
export const fetchTargetPortfolio = async () => (await api.get<TargetPortfolio[]>('/api/portfolio/target')).data
export const fetchRiskResults = async () => (await api.get<RiskResult[]>('/api/risk/results?limit=50')).data
export const fetchRebalanceOrders = async () => (await api.get<RebalanceOrder[]>('/api/rebalance/orders?limit=50')).data
export const fetchBacktestRuns = async () => (await api.get<BacktestRun[]>('/api/backtest/runs?limit=20')).data
export const fetchBacktestCurve = async (id: number) => (await api.get<BacktestCurvePoint[]>(`/api/backtest/${id}/equity-curve`)).data
export const fetchBacktestMetrics = async (id: number) => (await api.get<BacktestMetric[]>(`/api/backtest/${id}/metrics`)).data
export const fetchReports = async () => (await api.get<Report[]>('/api/reports?limit=20')).data
export const fetchReport = async (id: number) => (await api.get<Report>(`/api/reports/${id}`)).data
export const syncCalendar = async (payload: { start_date: string; end_date: string; market?: string }) =>
  (await api.post<RunSummary>('/api/calendar/sync', payload)).data
export const syncMarket = async (payload: { symbols?: string[]; start_date?: string; end_date?: string; max_symbols?: number; clean_after_sync?: boolean }) =>
  (await api.post<RunSummary>('/api/market/sync', payload)).data
export const checkDataQuality = async (payload: { symbols: string[]; start_date: string; end_date: string }) =>
  (await api.post<RunSummary[]>('/api/data-quality/check', payload)).data
export const calculateFactors = async (payload: { symbols?: string[]; start_date?: string; end_date?: string }) =>
  (await api.post<RunSummary>('/api/factors/calculate', payload)).data
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
  strategy_code: string
  portfolio_value?: number
  generate_report?: boolean
}) => (await api.post<{ task_id: number; status: string }>('/api/workflows/run', payload)).data
export const fetchWorkflowTask = async (taskId: number) =>
  (await api.get<WorkflowTask>(`/api/workflows/${taskId}`)).data
