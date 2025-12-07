"""
Trade model for tracking trade history.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
import enum

from app.domains.trading.models.db import Base


class TradeType(enum.Enum):
    """Trade type enum."""

    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(enum.Enum):
    """Trade status enum."""

    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Trade(Base):
    """Trade model for tracking trade history."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True, index=True)
    stock_symbol = Column(String(50), nullable=False, index=True)
    trade_type = Column(SQLEnum(TradeType), nullable=False)

    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    order_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.PENDING, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Trade(id={self.id}, stock={self.stock_symbol}, type={self.trade_type.value}, price={self.price})>"

