"""
Performance model for tracking daily trading performance.
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from app.domains.trading.models.db import Base


class Performance(Base):
    """Performance model for tracking daily trading performance."""

    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)

    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)

    total_pnl = Column(Float, default=0.0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)
    max_drawdown = Column(Float, default=0.0, nullable=False)
    consecutive_losses = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("date", name="unique_performance_date"),)

    def __repr__(self):
        return f"<Performance(date={self.date}, total_pnl={self.total_pnl}, win_rate={self.win_rate})>"

