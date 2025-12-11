"""
Position manager for tracking positions and calculating P&L.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from app.domains.trading.models.position import Position, PositionStatus
from app.domains.trading.models.db import get_session
from app.domains.trading.kite_client import KiteClient
from app.shared.config import config
from app.shared.logger import logger


class PositionManager:
    """Position manager for tracking and managing stock positions."""

    def __init__(self, kite_client: Optional[KiteClient] = None):
        """Initialize position manager."""
        self.session = get_session()
        self.kite_client = kite_client

    def create_position(
        self,
        stock_symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        take_profit: float,
    ) -> Position:
        """Create a new position record."""
        try:
            position = Position(
                stock_symbol=stock_symbol,
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status=PositionStatus.ACTIVE,
                entry_time=datetime.utcnow(),
            )
            self.session.add(position)
            self.session.commit()
            logger.info(
                f"✅ Created position: {stock_symbol} @ {entry_price} x {quantity} "
                f"(SL: {stop_loss}, TP: {take_profit})"
            )
            return position
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error creating position: {e}")
            raise

    def update_position(self, position_id: int, **kwargs) -> Optional[Position]:
        """Update position with new values."""
        try:
            position = (
                self.session.query(Position).filter(Position.id == position_id).first()
            )
            if not position:
                logger.error(f"❌ Position {position_id} not found")
                return None

            for key, value in kwargs.items():
                if hasattr(position, key):
                    setattr(position, key, value)

            position.updated_at = datetime.utcnow()
            self.session.commit()
            return position
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error updating position: {e}")
            return None

    def get_active_positions(self) -> List[Position]:
        """Fetch all active positions."""
        try:
            positions = (
                self.session.query(Position)
                .filter(Position.status == PositionStatus.ACTIVE)
                .all()
            )
            return positions
        except Exception as e:
            logger.error(f"❌ Error fetching active positions: {e}")
            return []

    def get_position_by_symbol(self, stock_symbol: str) -> Optional[Position]:
        """Get active position for a specific stock (legacy method, returns first)."""
        try:
            position = (
                self.session.query(Position)
                .filter(
                    Position.stock_symbol == stock_symbol,
                    Position.status == PositionStatus.ACTIVE,
                )
                .first()
            )
            return position
        except Exception as e:
            logger.error(f"❌ Error fetching position for {stock_symbol}: {e}")
            return None

    def get_positions_by_symbol(self, stock_symbol: str) -> List[Position]:
        """Get all active positions for a specific stock."""
        try:
            positions = (
                self.session.query(Position)
                .filter(
                    Position.stock_symbol == stock_symbol,
                    Position.status == PositionStatus.ACTIVE,
                )
                .all()
            )
            return positions
        except Exception as e:
            logger.error(f"❌ Error fetching positions for {stock_symbol}: {e}")
            return []

    def count_positions_today(self, stock_symbol: str) -> int:
        """Count all positions (active + closed) created today for a specific stock."""
        try:
            from datetime import date, time

            today = date.today()
            today_start = datetime.combine(today, time.min)
            count = (
                self.session.query(Position)
                .filter(
                    Position.stock_symbol == stock_symbol,
                    Position.created_at >= today_start,
                )
                .count()
            )
            return count
        except Exception as e:
            logger.error(f"❌ Error counting positions for {stock_symbol}: {e}")
            return 0

    def calculate_position_size(self, total_capital: float) -> float:
        """Calculate position size based on capital allocation."""
        position_size_percent = config.POSITION_SIZE_PERCENT / 100.0
        return total_capital * position_size_percent

    def calculate_stop_loss(
        self,
        entry_price: float,
        stop_loss_percent: float = 2.0,
        exchange: str = "NSE",
        symbol: str = None,
    ) -> float:
        """
        Calculate stop-loss price (default: 2% below entry).
        Rounds to tick size if symbol and kite_client are available.
        """
        sl_price = entry_price * (1 - stop_loss_percent / 100.0)

        # Round to tick size if kite_client is available
        if self.kite_client and symbol:
            try:
                tick_size = self.kite_client.get_tick_size(exchange, symbol)
                sl_price = self.kite_client.round_to_tick_size(sl_price, tick_size)
            except Exception as e:
                logger.warning(
                    f"⚠️  Could not round stop-loss to tick size for {symbol}: {e}"
                )

        return sl_price

    def calculate_take_profit(
        self,
        entry_price: float,
        take_profit_percent: float = 4.0,
        exchange: str = "NSE",
        symbol: str = None,
    ) -> float:
        """
        Calculate take-profit price (default: 4% above entry).
        Rounds to tick size if symbol and kite_client are available.
        """
        tp_price = entry_price * (1 + take_profit_percent / 100.0)

        # Round to tick size if kite_client is available
        if self.kite_client and symbol:
            try:
                tick_size = self.kite_client.get_tick_size(exchange, symbol)
                tp_price = self.kite_client.round_to_tick_size(tp_price, tick_size)
            except Exception as e:
                logger.warning(
                    f"⚠️  Could not round take-profit to tick size for {symbol}: {e}"
                )

        return tp_price

    def close_position(
        self, position_id: int, exit_price: float, exit_reason: str
    ) -> Optional[Position]:
        """Close a position and calculate P&L."""
        try:
            position = (
                self.session.query(Position).filter(Position.id == position_id).first()
            )
            if not position:
                logger.error(f"❌ Position {position_id} not found")
                return None

            # Calculate P&L
            pnl = (exit_price - position.entry_price) * position.quantity
            pnl_percent = (
                (exit_price - position.entry_price) / position.entry_price
            ) * 100.0

            # Determine status based on exit reason
            status_map = {
                "TAKE_PROFIT": PositionStatus.CLOSED_PROFIT,
                "STOP_LOSS": PositionStatus.CLOSED_LOSS,
                "PRICE_BELOW_CLOUD": PositionStatus.CLOSED_REVERSAL,
                "MACD_CROSSED_BELOW_SIGNAL": PositionStatus.CLOSED_REVERSAL,  # Legacy reason
                "MACD_REVERSAL": PositionStatus.CLOSED_REVERSAL,
                "EOD": PositionStatus.CLOSED_EOD,
            }
            status = status_map.get(exit_reason, PositionStatus.CLOSED_LOSS)

            # Update position
            position.exit_price = exit_price
            position.exit_time = datetime.utcnow()
            position.pnl = pnl
            position.exit_reason = exit_reason
            position.status = status

            self.session.commit()

            logger.info(
                f"✅ Closed position: {position.stock_symbol} @ {exit_price} "
                f"(P&L: {pnl:.2f}, {pnl_percent:.2f}%) - {exit_reason}"
            )

            return position
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error closing position: {e}")
            return None

    def get_unrealized_pnl(self, position: Position, current_price: float) -> float:
        """Calculate unrealized P&L for a position."""
        return (current_price - position.entry_price) * position.quantity

    def update_position_status(self, position_id: int, status: PositionStatus) -> bool:
        """Update position status."""
        try:
            position = (
                self.session.query(Position).filter(Position.id == position_id).first()
            )
            if not position:
                return False

            position.status = status
            position.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error updating position status: {e}")
            return False
