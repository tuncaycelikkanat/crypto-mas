// Health & System
export interface HealthStatus {
  status: string;
  uptime_seconds?: number;
  version?: string;
}

export interface DatabaseHealth {
  status: string;
  table_count?: number;
}

// Bot Management
export interface BotInfo {
  bot_id: string;
  status: 'RUNNING' | 'STOPPED' | 'ERROR' | string;
  exchange: string;
  symbols: string[];
  risk_level: number;
  mode: string;
  timeframe?: string;
}

export interface BotStatusResponse {
  bots: BotInfo[];
  total?: number;
}

// Paper Trading
export interface PaperAccount {
  name?: string;
  exchange?: string;
  cash_balance: number | string;
  equity: number | string;
  unrealized_pnl?: number | string;
  margin_used?: number | string;
  open_positions?: OpenPosition[];
  closed_positions?: ClosedPosition[];
}

export interface ClosedPosition {
  symbol: string;
  exchange?: string;
  side: 'LONG' | 'SHORT' | string;
  quantity: number | string;
  entry_price: number | string;
  current_price: number | string;
  realized_pnl: number | string;
  opened_at: string;
  closed_at: string;
  close_reason: string;
}

export interface OpenPosition {
  id?: number;
  account_name?: string;
  exchange?: string;
  symbol: string;
  side: 'LONG' | 'SHORT' | string;
  quantity: number | string;
  entry_price: number | string;
  current_price?: number | string;
  unrealized_pnl: number | string;
  stop_loss_price?: number | null;
  take_profit_price?: number | null;
  strategy_mode?: string | null;
  opened_at?: string;
}

export interface TradeRecord {
  id: number;
  symbol: string;
  side: string;
  quantity: number | string;
  price: number | string;
  notional: number | string;
  realized_pnl: number | null;
  reason?: string;
  executed_at: string;
}

export interface AnalyticsSummary {
  total_trades: number;
  winning_trades?: number;
  losing_trades?: number;
  win_rate: number;
  total_pnl: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  profit_factor?: number;
  open_positions?: number;
  equity?: number;
  current_balance?: number;
}

export interface EquityCurveData {
  data: EquityCurvePoint[];
}

export interface EquityCurvePoint {
  time: string;
  value: number;
  equity?: number;
}

export interface TradeHistoryResponse {
  history: TradeRecord[];
}

// Backtesting
export interface BacktestConfig {
  risk_level: number;
  use_btc_shield: boolean;
  use_htf_shield: boolean;
  use_regime_shield: boolean;
}

export interface BacktestJob {
  id?: string;
  job_id: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PENDING' | 'CANCELLED' | string;
  symbol?: string;
  symbols: string[];
  strategy?: string;
  strategy_name: string;
  exchange?: string;
  start_date?: string;
  end_date?: string;
  start_time: string;
  end_time: string;
  initial_balance: number;
  final_equity: number | null;
  total_fees_paid: number | null;
  total_trades: number | null;
  win_rate: number | null;
  max_drawdown: number | null;
  config_json: BacktestConfig | null;
  result?: BacktestResult;
}

export interface BacktestResult {
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  equity_curve: EquityCurvePoint[];
}

// Analytics
export interface PerformanceSummary {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  sharpe_ratio: number;
  max_drawdown: number;
  profit_factor: number;
}

// Decisions / Live Logs
export interface DecisionLog {
  timestamp: string;
  stage: string;
  symbol: string;
  payload: Record<string, unknown>;
}

export interface LogEntry {
  id: number;
  cycle_id: number | null;
  level: string;
  stage: string;
  message: string;
  created_at: string;
  payload: any;
}

export interface LogsResponse {
  logs: LogEntry[];
  count: number;
}

// Risk Regime
export interface RegimeSnapshot {
  btc_regime: string;
  confidence: number;
  risk_multiplier: number;
}

export interface RiskSnapshot {
  max_drawdown_limit_pct: number;
  current_drawdown_pct: number;
  gross_exposure_pct: number;
  correlated_symbols_count: number;
  max_positions_allowed: number;
}

export interface RiskRegimeData {
  timestamp: string;
  system_status: string;
  trading_mode: string;
  regime_snapshot: RegimeSnapshot;
  risk_snapshot: RiskSnapshot;
}

export interface CycleResponse {
  status: string;
  reason?: string;
  symbols_processed?: number;
  decisions_made?: number;
  trades_executed?: number;
}

export interface CoinSymbolsResponse {
  symbols: string[];
}

export interface CoinDataResponse {
  symbol: string;
  timeframe: string;
  exchange: string;
  candles: any[];
  features?: Record<string, any>;
}
