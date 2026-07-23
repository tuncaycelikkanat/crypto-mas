from datetime import datetime, timezone
import json

from sqlalchemy import JSON, Column, DateTime, Integer, String, Float
from sqlalchemy.orm import declarative_base

from crypto_mas.infrastructure.db.base import Base

class OptimizationHistory(Base):
    __tablename__ = "optimization_history"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False, default="RUNNING")  # RUNNING, COMPLETED, FAILED
    triggered_by = Column(String(50), nullable=False)  # SCHEDULED, MANUAL
    strategy_name = Column(String(100), nullable=False)
    symbols_json = Column(JSON, nullable=False)
    lookback_months = Column(Integer, nullable=False)
    best_params_json = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
