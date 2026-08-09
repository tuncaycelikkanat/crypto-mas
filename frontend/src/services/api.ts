import axios from 'axios';
import type { 
  HealthStatus, DatabaseHealth, BotStatusResponse, 
  AnalyticsSummary, EquityCurveData, TradeHistoryResponse,
  PaperAccount, CycleResponse, BacktestJob, LogsResponse,
  RiskRegimeData, CoinSymbolsResponse, CoinDataResponse
} from '../types/api';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Health
export const getHealth = () => api.get<HealthStatus>('/health');
export const getDbHealth = () => api.get<DatabaseHealth>('/health/db');

// Bot
export const getBotStatus = () => api.get<BotStatusResponse>('/bot/status');
export const startBot = (data: any) => api.post('/bot/start', data);
export const stopBot = (bot_id: string) => api.post<BotStatusResponse>(`/bot/stop/${bot_id}`);
export const updateBotSymbols = (bot_id: string, data: { symbols: string[] }) => api.put(`/bot/symbols/${bot_id}`, data);
export const updateBotRisk = (bot_id: string, data: { risk_level: number }) => api.put(`/bot/risk/${bot_id}`, data);

// Analytics
export const getAnalyticsSummary = () => api.get<AnalyticsSummary>('/analytics/summary');
export const getEquityCurve = () => api.get<EquityCurveData>('/analytics/equity-curve');
export const getTradeHistory = () => api.get<TradeHistoryResponse>('/analytics/trade-history');
export const resetAnalytics = () => api.post('/analytics/reset');

// Paper Trading
export const getPaperAccount = () => api.get<PaperAccount>('/paper/mock/account');
export const initPaperAccount = () => api.post<PaperAccount>('/paper/mock/account/init');
export const runCycle = (data: any) => api.post<CycleResponse>('/cycle/run', data);

// Backtest
export const getBacktestJobs = () => api.get<BacktestJob[]>('/backtest');
export const deleteBacktestJob = (job_id: string) => api.delete(`/backtest/${job_id}`);
export const getBacktestCompareData = (job_id: string) => api.get(`/backtest/${job_id}/compare-data`);
export const runBacktest = (data: any) => api.post('/backtest/run', data);
export const cancelBacktestJob = (job_id: string) => api.post(`/backtest/${job_id}/cancel`);

// Logs
export const getRecentLogs = (account_name: string, limit: number) => api.get<any[]>(`/logs/recent?account_name=${account_name}&limit=${limit}`);
export const getAnalyticsLogs = (params: any) => api.get<LogsResponse>('/analytics/logs', { params });
export const deleteAnalyticsLogs = () => api.delete('/analytics/logs');

// Market Radar
export const getCoinSymbols = () => api.get<CoinSymbolsResponse>('/analytics/coins');
export const getCoinData = (symbol: string) => api.get<CoinDataResponse>(`/analytics/coin/${symbol}`);

export default api;
