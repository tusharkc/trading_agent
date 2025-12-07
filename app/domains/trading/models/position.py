"""
Position model for tracking open and closed positions.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import enum

from app.domains.trading.models.db import Base


class PositionStatus(enum.Enum):
    """Position status enum."""

    UNMONITORED = "UNMONITORED"
    WATCHING = "WATCHING"
    ACTIVE = "ACTIVE"
    CLOSED_PROFIT = "CLOSED_PROFIT"
    CLOSED_LOSS = "CLOSED_LOSS"
    CLOSED_REVERSAL = "CLOSED_REVERSAL"
    CLOSED_EOD = "CLOSED_EOD"


class Position(Base):
    """Position model for tracking stock positions."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_symbol = Column(String(50), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.UNMONITORED, nullable=False)

    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    pnl = Column(Float, default=0.0, nullable=False)
    exit_reason = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Position(id={self.id}, stock={self.stock_symbol}, status={self.status.value}, pnl={self.pnl})>"

