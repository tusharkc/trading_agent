"""
Order model for tracking order status.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
import enum

from app.domains.trading.models.db import Base


class OrderType(enum.Enum):
    """Order type enum."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"  # Stop Loss Market


class TransactionType(enum.Enum):
    """Transaction type enum."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(enum.Enum):
    """Order status enum."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Order(Base):
    """Order model for tracking order status."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_symbol = Column(String(50), nullable=False, index=True)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)

    price = Column(Float, nullable=True)  # None for market orders
    quantity = Column(Integer, nullable=False)

    kite_order_id = Column(String(100), nullable=True, unique=True, index=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)

    filled_price = Column(Float, nullable=True)
    filled_quantity = Column(Integer, default=0, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Order(id={self.id}, stock={self.stock_symbol}, type={self.order_type.value}, status={self.status.value})>"

