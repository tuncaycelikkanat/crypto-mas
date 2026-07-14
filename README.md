<div align="center">

<br/>

```
  ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗
 ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗
 ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║
 ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║
 ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝
  ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝
                      M A S
```

**Crypto Multi-Agent System**

*A risk-first, explainable, portfolio-aware crypto trading engine*

<br/>

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PG16-FDB515?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## What Is This?

**Crypto MAS** is a trading engine built around one core conviction: *most automated trading systems fail not because of bad signals, but because of bad risk management.*

This project is an attempt to build something different — a system where every decision passes through multiple independent agents, each asking a different question, before a single position is considered.

It is not a bot that promises returns. It is a framework for making **structured, explainable, and risk-bounded** trading decisions in the crypto markets.

---

## The Philosophy

### Risk First, Always

Every component in this system is designed around the constraint that **protecting capital matters more than capturing upside.** A signal can be strong and still be rejected — by the regime filter, by the scoring threshold, by the portfolio limits, or by the final risk engine. The pipeline is built to say *no* more often than it says *yes.*

### Explainability Over Black Boxes

Every agent produces a human-readable `reason` alongside its output. You can always trace back *why* a signal was generated, *why* a score came out the way it did, *why* a position was rejected. There are no opaque model outputs, no unexplained scores.

### Designed to Be Backtestable

The system is built from the ground up with a clean adapter layer between decision logic and execution. The same pipeline that runs against live market data can run against historical candles through a `BacktestBrokerAdapter` — with no changes to the core logic. Decisions are data, not side effects.

---

## How Decisions Are Made

The system follows a multi-stage pipeline. Each stage is an independent agent with a single responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Market Data Layer                          │
│              (Binance · Mock · Historical)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │  OHLCV candles
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Feature Pipeline                            │
│          EMA · SMA · RSI · ATR · ROC  (pure Python)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │  feature snapshots
                            ▼
┌──────────────┐   ┌────────────────┐   ┌─────────────────────────┐
│ Signal Agent │   │  Scoring Agent │   │     Regime Agent        │
│              │   │                │   │                         │
│ Is there a   │   │ How strong is  │   │ What is the market      │
│ trend signal?│   │ the signal?    │   │ doing right now?        │
│              │   │                │   │ Bull · Bear · Sideways  │
│ LONG / SHORT │   │  0.0 → 1.0     │   │ HIGH_VOLATILITY         │
│ NEUTRAL      │   │                │   │                         │
└──────┬───────┘   └───────┬────────┘   └────────────┬────────────┘
       │                   │                         │
       └───────────────────┴─────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Decision Orchestrator                         │
│                                                                 │
│   Combines signal · score · regime into a single decision:      │
│   CONSIDER_LONG · CONSIDER_SHORT · HOLD · AVOID                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Portfolio Manager Agent                        │
│                                                                 │
│   Selects the best candidates from all symbols.                 │
│   Allocates weights proportionally to conviction score.         │
│   Enforces position limits and gross exposure caps.             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Risk Engine Agent                           │
│                                                                 │
│   Final gatekeeper. Checks every constraint before approval:    │
│   max positions · max gross exposure · min cash weight          │
│   max single position weight                                    │
│                                                                 │
│   → APPROVED · REDUCED · REJECTED                               │
└─────────────────────────────────────────────────────────────────┘
```

No position reaches execution without passing through every layer.

---

## Architecture

The codebase follows a strict layered architecture based on Domain-Driven Design principles:

```
src/crypto_mas/
│
├── domain/           # Pure business logic. No framework dependencies.
│   ├── models/       # SQLAlchemy ORM models (Candle, Symbol, Position…)
│   ├── repositories/ # Data access abstractions
│   └── events/       # Domain event definitions and in-memory publisher
│
├── infrastructure/   # Everything that touches the outside world.
│   ├── db/           # Engine, session factory
│   ├── cache/        # Redis client
│   ├── config/       # Pydantic settings (env-driven)
│   └── time/         # Mockable time provider for testability
│
├── services/         # Orchestration and use cases.
│   ├── market_data_service/   # Provider abstraction + historical fetcher
│   ├── feature_pipeline/      # Indicator calculation + snapshot storage
│   ├── decision_orchestrator/ # Multi-symbol decision runner
│   └── oms/                   # Order Management System (interface + paper impl)
│
├── engine/           # Decision-making units. Each engine has one job.
│   ├── signal/                # Trend signal generation (TrendSignalEngine)
│   ├── scoring/               # Signal strength scoring (ScoringEngine)
│   ├── regime/                # Market regime detection (RegimeEngine)
│   ├── portfolio/             # Target portfolio construction (PortfolioEngine)
│   ├── risk/                  # Risk limit enforcement (RiskEngine + profiles)
│   ├── backtest/              # Backtest simulation engine
│   └── strategy/              # Strategy wrappers (multi_agent, ema_golden_cross…)
│
├── brokers/          # Exchange adapter implementations.
│   ├── binance_adapter/       # Live Binance market data
│   ├── mock_adapter/          # Deterministic fake data for development
│   ├── paper_broker_adapter/  # Paper trading (no real orders)
│   └── backtest_broker_adapter/ # Historical simulation
│
└── apps/             # Entry points.
    ├── api/           # FastAPI HTTP interface
    ├── scheduler/     # Periodic job runner
    └── worker/        # Async background task executor
```

---

## Data Model

The system persists everything that matters:

| Table | Purpose |
|-------|---------|
| `candles` | Raw OHLCV market data with exchange + timeframe partitioning |
| `symbols` | Tracked trading pairs with metadata |
| `feature_snapshots` | Computed indicators stored per candle, per symbol |
| `positions` | Open and closed positions with full PnL tracking |
| `paper_accounts` | Virtual accounts for paper trading simulation |
| `config_versions` | Versioned strategy parameter sets |
| `system_events` | Audit log of significant system events |

The database is **TimescaleDB** — a PostgreSQL extension built for time-series workloads. Candle and feature tables are time-partitioned for efficient range queries across long historical windows.

---

## Trading Modes

The system is designed to operate in three modes without changing any core logic:

| Mode | Description |
|------|-------------|
| `BACKTEST` | Runs the full pipeline against historical candle data |
| `PAPER` | Live market data, simulated order execution, real PnL tracking |
| `LIVE` | Real orders sent to exchange via broker adapter *(future)* |

Mode switching is a single environment variable change.

---

## Current State

This project is in **active development**. The signal pipeline, scoring, regime detection, portfolio construction, and risk assessment layers are functional and tested. The scheduler, order management system, and live execution layer are works in progress.

> This is a research and engineering project. It is not financial advice. Do not use it to trade real money without fully understanding what it does.

---

<div align="center">

Built with Python · FastAPI · SQLAlchemy · TimescaleDB · Redis · Docker

</div>
