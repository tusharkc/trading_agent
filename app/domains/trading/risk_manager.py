"""
Risk manager for position limits, drawdown checks, and circuit breaker.
"""

from typing import List, Dict, Any
from datetime import datetime, date
from app.domains.trading.models.position import Position, PositionStatus
from app.domains.trading.models.performance import Performance
from app.domains.trading.models.db import get_session
from app.shared.config import config
from app.shared.logger import logger


class RiskManager:
    """Risk manager for enforcing trading limits and risk controls."""

    def __init__(self):
        """Initialize risk manager."""
        self.session = get_session()
        self.max_positions = config.MAX_POSITIONS
        self.max_daily_drawdown_percent = 18.0
        self.circuit_breaker_losses = 3
        self._position_limit_warning_logged = False  # Track if warning already logged

    def check_position_limit(self, current_active_positions: int) -> bool:
        """Verify active positions are below maximum limit."""
        if current_active_positions >= self.max_positions:
            if not self._position_limit_warning_logged:
                logger.warning(
                    f"⚠️  Position limit reached: {current_active_positions}/{self.max_positions}"
                )
                self._position_limit_warning_logged = True
            return False
        else:
            # Reset warning flag when below limit
            if self._position_limit_warning_logged:
                self._position_limit_warning_logged = False
        return True

    def check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is active (3 consecutive losses)."""
        try:
            today = date.today()
            performance = (
                self.session.query(Performance)
                .filter(Performance.date == today)
                .first()
            )

            if (
                performance
                and performance.consecutive_losses >= self.circuit_breaker_losses
            ):
                logger.warning(
                    f"🚨 Circuit breaker active: {performance.consecutive_losses} consecutive losses"
                )
                return False  # Trading blocked

            return True  # Trading allowed

        except Exception as e:
            logger.error(f"❌ Error checking circuit breaker: {e}")
            return True  # Allow trading on error

    def calculate_portfolio_drawdown(
        self, positions: List[Position], current_prices: Dict[str, float]
    ) -> float:
        """
        Calculate total portfolio P&L (drawdown).
        Args:
            positions: List of active positions
            current_prices: Dict mapping stock_symbol to current_price
        Returns:
            Total portfolio P&L
        """
        total_pnl = 0.0
        for position in positions:
            current_price = current_prices.get(position.stock_symbol)
            if current_price:
                pnl = (current_price - position.entry_price) * position.quantity
                total_pnl += pnl
        return total_pnl

    def check_daily_drawdown_limit(
        self, portfolio_pnl: float, initial_capital: float
    ) -> bool:
        """
        Verify portfolio drawdown is within daily limit (18%).
        Args:
            portfolio_pnl: Current portfolio P&L
            initial_capital: Initial trading capital
        Returns:
            True if within limit, False if exceeded
        """
        if initial_capital <= 0:
            return True

        drawdown_percent = abs(portfolio_pnl / initial_capital) * 100.0

        if drawdown_percent >= self.max_daily_drawdown_percent:
            logger.warning(
                f"⚠️  Daily drawdown limit exceeded: {drawdown_percent:.2f}% >= {self.max_daily_drawdown_percent}%"
            )
            return False

        return True

    def should_trade(
        self,
        current_active_positions: int,
        portfolio_pnl: float = 0.0,
        initial_capital: float = 0.0,
    ) -> bool:
        """
        Main method to check if trading is allowed.
        Returns True if all risk checks pass.
        """
        # Check position limit
        if not self.check_position_limit(current_active_positions):
            return False

        # Check circuit breaker
        if not self.check_circuit_breaker():
            return False

        # Check daily drawdown limit (if negative P&L)
        if portfolio_pnl < 0:
            if not self.check_daily_drawdown_limit(portfolio_pnl, initial_capital):
                return False

        return True

    def increment_consecutive_losses(self) -> int:
        """Increment consecutive losses counter for today."""
        try:
            today = date.today()
            performance = (
                self.session.query(Performance)
                .filter(Performance.date == today)
                .first()
            )

            if not performance:
                # Create new performance record
                performance = Performance(date=today, consecutive_losses=1)
                self.session.add(performance)
            else:
                performance.consecutive_losses += 1

            self.session.commit()
            logger.info(f"📊 Consecutive losses: {performance.consecutive_losses}")
            return performance.consecutive_losses

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error incrementing consecutive losses: {e}")
            return 0

    def reset_consecutive_losses(self) -> bool:
        """Reset consecutive losses counter (e.g., after a winning trade)."""
        try:
            today = date.today()
            performance = (
                self.session.query(Performance)
                .filter(Performance.date == today)
                .first()
            )

            if performance:
                performance.consecutive_losses = 0
                self.session.commit()
                logger.info("✅ Consecutive losses reset")

            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error resetting consecutive losses: {e}")
            return False

    def reset_daily_counters(self):
        """Reset daily counters at start of new trading day."""
        try:
            today = date.today()
            performance = (
                self.session.query(Performance)
                .filter(Performance.date == today)
                .first()
            )

            if not performance:
                # Create new performance record for today
                performance = Performance(
                    date=today,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    total_pnl=0.0,
                    win_rate=0.0,
                    max_drawdown=0.0,
                    consecutive_losses=0,
                )
                self.session.add(performance)
                self.session.commit()
                logger.info(f"✅ Initialized daily performance record for {today}")

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error resetting daily counters: {e}")

    def update_performance(
        self,
        is_win: bool,
        pnl: float,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
    ):
        """Update daily performance metrics."""
        try:
            today = date.today()
            performance = (
                self.session.query(Performance)
                .filter(Performance.date == today)
                .first()
            )

            if not performance:
                performance = Performance(date=today)
                self.session.add(performance)

            performance.total_trades = total_trades
            performance.winning_trades = winning_trades
            performance.losing_trades = losing_trades
            performance.total_pnl += pnl
            performance.win_rate = (
                (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
            )

            # Update max drawdown if current P&L is worse
            if performance.total_pnl < performance.max_drawdown:
                performance.max_drawdown = performance.total_pnl

            self.session.commit()

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error updating performance: {e}")
