# Optuna Hyperparameter Optimization History

This document records the historical runs of the Optuna Hyperparameter Tuning algorithms applied to the Kanas strategy. 

## Multi-Regime Optimization (July 21, 2026)

**Objective Function**: `Score = Final Equity + (Win Rate * 1000)`
**Symbols Evaluated**: `["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]`

The system was optimized across three different market conditions to prevent overfitting and to extract the fundamental market psychology of each regime.

### 1. Bull Regime Optimization
- **Timeframe Evaluated**: February 15, 2024 to March 1, 2024
- **Market Context**: Aggressive uptrend leading to all-time highs.
- **Best Score**: 10460.87
- **Best Parameters Discovered**:
  - `min_adx`: 21.0
  - `rsi_threshold`: 50.0
  - `tp_rsi`: 84.0
  - `max_dist_ema`: 0.005
  - `tp_dist_ema`: 0.021
  - `max_rvol_pullback`: 1.3

*Psychology extracted*: Do not wait for a deep dip to enter; buy shallow pullbacks (RSI 50, dist_ema 0.5%). Hold the trade for a long time until extreme greed (RSI 84) to maximize profits. Avoid entering if volume is aggressively high during the pullback (RVOL 1.3).

### 2. Bear Regime Optimization
- **Timeframe Evaluated**: April 10, 2024 to April 25, 2024
- **Market Context**: Sharp bearish dumps and downside volatility.
- **Best Score**: 10229.38
- **Best Parameters Discovered**:
  - `min_adx`: 22.0
  - `rsi_threshold`: 50.0 (Reverse scaled to 50 for shorts)
  - `tp_rsi`: 21.0 (Reverse scaled to 79 for shorts)
  - `min_dist_ema`: 0.014
  - `max_dist_ema`: 0.030
  - `tp_dist_ema`: -0.016
  - `max_rvol_pullback`: 1.5

*Psychology extracted*: Wait for a relatively strong bounce to the EMA (1.4% to 3.0%) before shorting. Let the short ride until the market capitulates (RSI 21). Do not short into massive volume pumps (RVOL 1.5) as they might be short squeezes.

### 3. Sideways Regime Optimization
- **Timeframe Evaluated**: June 1, 2026 to June 15, 2026
- **Market Context**: Low volume, choppy consolidation.
- **Best Score**: 10176.26
- **Best Parameters Discovered**:
  - `min_adx`: 10.0
  - `max_adx`: 16.0
  - `rsi_oversold`: 26.0
  - `rsi_overbought`: 62.0

*Psychology extracted*: In a sideways market, do not trust normal "oversold" signals. Wait until the market is extremely oversold (RSI 26) to buy the bottom of the range. The top of the range gets rejected earlier, so short at RSI 62.

---
*Note: These optimal parameters were committed as the default configuration values for `BullTactic`, `BearTactic`, and `SidewaysTactic` on July 21, 2026.*
