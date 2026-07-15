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
  is_leveraged?: boolean
  is_inverse?: boolean
  fund_company?: string | null
  tracking_index?: string | null
  listing_date?: string | null
  fund_size?: string | null
  management_fee?: string | null
  custody_fee?: string | null
  expense_ratio?: string | null
  tracking_error?: string | null
  latest_premium_rate?: string | null
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
  fund_company?: string | null
  tracking_index?: string | null
  listing_date?: string | null
  fund_size?: number | null
  management_fee?: number | null
  custody_fee?: number | null
  expense_ratio?: number | null
  tracking_error?: number | null
  latest_premium_rate?: number | null
  description?: string | null
}

export interface HealthStatus {
  status: string
  service: string
  environment: string
  workflow_execution_mode?: string
}

export interface AssetUniverseSyncResponse {
  source: string
  total: number
  inserted_or_updated: number
}

export interface AssetProfileSyncResponse {
  source: string
  total: number
  updated: number
  skipped: number
  failed: number
  results: Array<{
    symbol: string
    status: string
    updated_fields: string[]
    message?: string | null
  }>
}

export interface AssetSyncLog {
  id: number
  sync_type: string
  source: string
  status: string
  total: number
  updated: number
  skipped: number
  failed: number
  message?: string | null
  details?: Record<string, unknown> | null
  created_at: string
}

export interface EtfCompareMetric {
  symbol: string
  name: string | null
  asset_class: string | null
  asset_region: string | null
  risk_level: number | null
  first_trade_date: string | null
  latest_trade_date: string | null
  latest_close: string | null
  bars: number
  total_return: string | null
  annualized_return: string | null
  annualized_volatility: string | null
  downside_volatility: string | null
  max_drawdown: string | null
  sharpe_ratio: string | null
  sortino_ratio: string | null
  calmar_ratio: string | null
  positive_day_rate: string | null
  estimated_gap_ratio: string | null
  average_amount: string | null
  tradability_score: number
  tradability_level: string
  tradability_notes: string[]
  buy_score: number
  buy_level: string
  buy_notes: string[]
}

export interface EtfCompareSeriesPoint {
  trade_date: string
  value: string
}

export interface EtfCorrelationCell {
  symbol_x: string
  symbol_y: string
  correlation: string | null
}

export interface EtfCompareResponse {
  start_date: string | null
  end_date: string | null
  metrics: EtfCompareMetric[]
  normalized_series: Record<string, EtfCompareSeriesPoint[]>
  correlations: EtfCorrelationCell[]
}

export interface EtfScreenerResponse {
  start_date: string | null
  end_date: string | null
  scope: string
  total_candidates: number
  returned: number
  metrics: EtfCompareMetric[]
}

export interface EtfDetailCurvePoint {
  trade_date: string
  close: string
  normalized_value: string
  drawdown: string
  amount: string | null
}

export interface EtfAlternativeCandidate {
  symbol: string
  name: string
  fund_company: string | null
  tracking_index: string | null
  fund_size: string | null
  expense_ratio: string | null
  average_amount: string | null
  tradability_score: number
  recommendation_score: number
  recommendation_level: string
  reasons: string[]
}

export interface EtfDecisionSummary {
  action: string
  score: number
  level: string
  confidence: string
  position_hint: string
  entry_plan: string
  stop_loss_hint: string
  data_quality: string
  reasons: string[]
  risks: string[]
  next_steps: string[]
}

export interface EtfDetailResponse {
  symbol: string
  asset: Asset | null
  metric: EtfCompareMetric
  decision: EtfDecisionSummary
  latest_factor: Factor | null
  alternatives: EtfAlternativeCandidate[]
  curve: EtfDetailCurvePoint[]
  recent_bars: MarketBarRead[]
}

export interface AgentOpinion {
  role: string
  title: string
  stance: string
  score: number
  summary: string
  evidence: string[]
  risks: string[]
  suggestion: string
}

export interface EtfAgentAnalysisResponse {
  symbol: string
  name: string | null
  start_date: string
  end_date: string
  data_status: string
  llm_enabled: boolean
  llm_used: boolean
  llm_model: string | null
  final_action: string
  final_score: number
  final_summary: string
  manager_commentary: string
  agents: AgentOpinion[]
  warnings: string[]
}

export interface EtfAgentAnalysisLog extends EtfAgentAnalysisResponse {
  id: number
  created_at: string
}

export interface MarketBarRead {
  symbol: string
  trade_date: string
  open: string | null
  high: string | null
  low: string | null
  close: string | null
  volume: string | null
  amount: string | null
  source: string | null
  data_status: string | null
  created_at: string
}

export interface DataQualityStatus {
  total_logs: number
  error_logs: number
  warning_logs: number
  latest_created_at: string | null
  status: string
  history_total_logs?: number
  history_error_logs?: number
  history_warning_logs?: number
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

export interface MarketSyncPlanItem {
  symbol: string
  name: string | null
  categories: string[]
  latest_trade_date: string | null
  has_clean_price: boolean
  range_bar_count: number
  range_latest_trade_date: string | null
  expected_bar_count: number | null
  missing_bar_count: number | null
  coverage_ratio: number | null
  sample_status: string
  sample_message: string | null
}

export interface MarketSyncPlan {
  sync_scope: string
  total_symbols: number
  missing_price_count: number
  ready_count: number
  insufficient_count: number
  empty_count: number
  recommended_sync_symbols: string[]
  expected_bar_count: number | null
  min_bars: number
  symbols: MarketSyncPlanItem[]
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
  alternatives: EtfAlternativeCandidate[]
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

export interface StrategyConfig {
  strategy_code: string
  strategy_name: string
  version: string
  rebalance_frequency: string
  config: Record<string, unknown>
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface DataSourceProvider {
  id: number | null
  provider_code: string
  provider_name: string
  provider_type: string
  enabled: boolean
  configured: boolean
  base_url: string | null
  auth_type: string
  token_masked: string | null
  request_interval_seconds: number | null
  max_requests_per_minute: number | null
  quota_per_minute: number | null
  quota_per_day: number | null
  status: string
  adapter_status: string
  used_by: string[]
  supported_usages: string[]
  notes: string[]
}

export interface DataSourceSettings {
  default_calendar_source: string
  default_market_source: string
  default_profile_source: string
  default_ai_provider: string
  providers: DataSourceProvider[]
}

export interface NewsArticle {
  id: number
  source: string
  external_id: string
  title: string
  source_name: string | null
  url: string | null
  image_url: string | null
  publish_time: string | null
  summary: string | null
  keywords: string[]
  related_symbols: string[]
  related_asset_class: string[]
  related_region: string[]
  sentiment_score: number | null
  impact_level: string | null
  created_at: string
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

export const fetchHealth = async () => (await api.get<HealthStatus>('/health')).data
export const fetchLiveHealth = async () => (await api.get<HealthStatus>('/health/live')).data
export const fetchReadyHealth = async () => (await api.get<HealthStatus>('/health/ready')).data
export const fetchAuthStatus = async () => (await api.get<AuthStatus>('/api/auth/status')).data
export const login = async (payload: { username: string; password: string }) =>
  (await api.post<AuthStatus>('/api/auth/login', payload)).data
export const logout = async () => (await api.post<AuthStatus>('/api/auth/logout')).data
export const fetchAssets = async (params?: { enabled?: boolean; q?: string; limit?: number }) =>
  (await api.get<Asset[]>('/api/assets', { params })).data
export const batchUpsertAssets = async (payload: { items: AssetUpsertItem[] }) =>
  (await api.post<{ total: number; inserted_or_updated: number }>('/api/assets/batch-upsert', payload)).data
export const seedCuratedAssets = async () =>
  (await api.post<{ total: number; inserted_or_updated: number }>('/api/assets/seed-curated')).data
export const syncAssetUniverse = async (payload: { source?: string; limit?: number }) =>
  (await api.post<AssetUniverseSyncResponse>('/api/assets/sync-universe', payload, { timeout: 300000 })).data
export const syncAssetProfiles = async (payload: { source?: string; symbols?: string[]; limit?: number; preserve_existing?: boolean }) =>
  (await api.post<AssetProfileSyncResponse>('/api/assets/sync-profiles', payload)).data
export const fetchAssetSyncLogs = async (params?: { sync_type?: string; limit?: number }) =>
  (await api.get<AssetSyncLog[]>('/api/assets/sync-logs', { params })).data
export const updateAsset = async (symbol: string, payload: {
  enabled?: boolean
  risk_level?: number
  fund_company?: string | null
  tracking_index?: string | null
  listing_date?: string | null
  fund_size?: number | null
  management_fee?: number | null
  custody_fee?: number | null
  expense_ratio?: number | null
  tracking_error?: number | null
  latest_premium_rate?: number | null
  description?: string | null
}) =>
  (await api.patch<Asset>(`/api/assets/${symbol}`, payload)).data
export const compareEtfs = async (payload: { symbols: string[]; start_date?: string; end_date?: string; auto_sync_missing?: boolean; max_auto_sync_symbols?: number }) =>
  (await api.post<EtfCompareResponse>('/api/etf-compare', payload)).data
export const screenEtfs = async (payload: {
  scope?: string
  symbols?: string[]
  start_date?: string
  end_date?: string
  limit?: number
  min_bars?: number
  min_tradability_score?: number
  min_buy_score?: number
  asset_class?: string
  asset_region?: string
  auto_sync_missing?: boolean
  max_auto_sync_symbols?: number
}) => (await api.post<EtfScreenerResponse>('/api/etf-compare/screener', payload)).data
export const scoreEtfTradability = async (payload: { symbols: string[]; start_date?: string; end_date?: string }) =>
  (await api.post<EtfCompareMetric[]>('/api/etf-compare/tradability', payload)).data
export const fetchEtfDetail = async (symbol: string, params?: { start_date?: string; end_date?: string }) =>
  (await api.get<EtfDetailResponse>(`/api/etf-detail/${symbol}`, { params })).data
export const analyzeEtfAgents = async (payload: { symbol: string; start_date?: string; end_date?: string; use_llm?: boolean; auto_sync?: boolean }) =>
  (await api.post<EtfAgentAnalysisResponse>('/api/agent-analysis/etf', payload)).data
export const fetchEtfAgentAnalysisHistory = async (params?: { symbol?: string; limit?: number }) =>
  (await api.get<EtfAgentAnalysisLog[]>('/api/agent-analysis/etf/history', { params })).data
export const fetchDataQualityStatus = async () => (await api.get<DataQualityStatus>('/api/data-quality/status')).data
export const fetchDataQualityLogs = async () => (await api.get<DataQualityLog[]>('/api/data-quality/logs?limit=50')).data
export const fetchMarketSyncPlan = async (syncScope = 'core', params?: { start_date?: string; end_date?: string; min_bars?: number }) =>
  (await api.get<MarketSyncPlan>('/api/market/sync-plan', { params: { sync_scope: syncScope, ...params } })).data
export const fetchFactorRanking = async () => (await api.get<Factor[]>('/api/factors/ranking?limit=50')).data
export const fetchTargetPortfolio = async () => (await api.get<TargetPortfolio[]>('/api/portfolio/target')).data
export const fetchPositions = async () => (await api.get<PortfolioPosition[]>('/api/portfolio/positions')).data
export const fetchPortfolioXray = async () => (await api.get<PortfolioXray>('/api/portfolio/xray')).data
export const resolvePositionSymbols = async (symbols: string[], options?: { auto_sync?: boolean; source?: string }) =>
  (await api.post<PositionResolveResult[]>('/api/portfolio/positions/resolve', {
    symbols,
    auto_sync: options?.auto_sync ?? false,
    source: options?.source || 'akshare',
  })).data
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
  sync_scope?: string
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
export const fetchStrategies = async () => (await api.get<StrategyConfig[]>('/api/strategies')).data
export const createStrategy = async (payload: {
  strategy_code: string
  strategy_name: string
  version?: string
  rebalance_frequency?: string
  config?: Record<string, unknown>
  enabled?: boolean
}) => (await api.post<StrategyConfig>('/api/strategies', payload)).data
export const updateStrategy = async (strategyCode: string, payload: {
  strategy_name?: string
  version?: string
  rebalance_frequency?: string
  config?: Record<string, unknown>
  enabled?: boolean
}) => (await api.patch<StrategyConfig>(`/api/strategies/${strategyCode}`, payload)).data
export const runStrategy = async (payload: { strategy_code: string; run_date?: string; run_type?: string }) =>
  (await api.post<RunSummary>('/api/strategies/run', payload)).data
export const fetchDataSourceSettings = async () => (await api.get<DataSourceSettings>('/api/settings/data-sources')).data
export const createDataSource = async (payload: {
  provider_code: string
  provider_name: string
  provider_type?: string
  enabled?: boolean
  base_url?: string | null
  auth_type?: string
  secret_value?: string | null
  request_interval_seconds?: number | null
  quota_per_minute?: number | null
  quota_per_day?: number | null
  supported_usages?: string[]
  adapter_status?: string
  notes?: string[]
}) => (await api.post<DataSourceProvider>('/api/settings/data-sources', payload)).data
export const updateDataSource = async (providerCode: string, payload: {
  provider_name?: string
  provider_type?: string
  enabled?: boolean
  base_url?: string | null
  auth_type?: string
  secret_value?: string | null
  clear_secret?: boolean
  request_interval_seconds?: number | null
  quota_per_minute?: number | null
  quota_per_day?: number | null
  supported_usages?: string[]
  adapter_status?: string
  notes?: string[]
}) => (await api.patch<DataSourceProvider>(`/api/settings/data-sources/${providerCode}`, payload)).data
export const fetchNews = async (params?: { symbol?: string; q?: string; limit?: number }) =>
  (await api.get<NewsArticle[]>('/api/news', { params })).data
export const fetchRelatedNews = async (symbol: string, params?: { limit?: number }) =>
  (await api.get<NewsArticle[]>(`/api/news/related/${symbol}`, { params })).data
export const syncNews = async (payload: { source?: string; num?: number; page?: number }) =>
  (await api.post<RunSummary>('/api/news/sync', payload)).data
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
  sync_scope?: string
  date_preset?: string
  start_date?: string
  end_date?: string
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
export const startHistoricalMarketInit = async (payload: {
  scope?: string
  symbols?: string[]
  years?: number
  start_date?: string
  end_date?: string
  source?: string
  calendar_source?: string
  incremental_sync?: boolean
  clean_after_sync?: boolean
  request_interval_seconds?: number
  max_symbols?: number
}) => (await api.post<{ task_id: number; status: string }>('/api/workflows/historical-init', payload)).data
export const fetchWorkflowTask = async (taskId: number) =>
  (await api.get<WorkflowTask>(`/api/workflows/${taskId}`)).data
export const fetchWorkflowTasks = async () =>
  (await api.get<WorkflowTask[]>('/api/workflows?limit=20')).data
export const cancelWorkflowTask = async (taskId: number) =>
  (await api.post<WorkflowTask>(`/api/workflows/${taskId}/cancel`)).data
export const retryFailedWorkflowTask = async (taskId: number) =>
  (await api.post<{ task_id: number; status: string }>(`/api/workflows/${taskId}/retry-failed`)).data
