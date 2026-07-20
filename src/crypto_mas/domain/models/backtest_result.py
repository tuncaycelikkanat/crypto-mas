from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from crypto_mas.infrastructure.db.base import Base


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True)
    
    status = Column(String(20), nullable=False, default="RUNNING")  # RUNNING, COMPLETED, FAILED
    
    exchange = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    strategy_name = Column(String(50), nullable=False, default="multi_agent")
    symbols = Column(JSON, nullable=False)
    config_json = Column(JSON, nullable=True)
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    initial_balance = Column(Float, nullable=False)
    final_equity = Column(Float, nullable=True)
    total_fees_paid = Column(Float, nullable=True)
    
    total_trades = Column(Integer, nullable=True, default=0)
    total_long = Column(Integer, nullable=True, default=0)
    total_short = Column(Integer, nullable=True, default=0)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    expectancy = Column(Float, nullable=True)   # avg expected PnL per trade
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    avg_trade_duration_s = Column(Float, nullable=True)  # seconds
    
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True), nullable=True)
