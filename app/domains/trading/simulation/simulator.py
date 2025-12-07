"""
Trading simulator for backtesting using historical data.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pytz import timezone

from app.domains.trading.technical_analyzer import TechnicalAnalyzer
from app.domains.trading.signal_generator import SignalGenerator
from app.domains.trading.position_manager import PositionManager
from app.domains.trading.risk_manager import RiskManager
from app.domains.trading.simulation.mock_kite_client import MockKiteClient
from app.domains.trading.models.db import init_db
from app.shared.logger import logger

# IST timezone
IST = timezone("Asia/Kolkata")


class TradingSimulator:
    """Simulates trading day using historical data."""

    def __init__(
        self,
        target_date: datetime,
        initial_capital: float,
        stock_list: List[str],
    ):
        """
        Initialize simulator.

        Args:
            target_date: Date to simulate (datetime object)
            initial_capital: Starting capital in rupees
            stock_list: List of stock symbols to simulate
        """
        self.target_date = target_date
        self.initial_capital = initial_capital
        self.stock_list = stock_list

        # Initialize database tables
        init_db()

        # Initialize components with mock client
        self.mock_kite = MockKiteClient(target_date=target_date)
        self.technical_analyzer = TechnicalAnalyzer()
        self.signal_generator = SignalGenerator()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager()

        # Simulation state - keep dates timezone-naive for consistency
        # Remove timezone if present, then set times
        target_date_naive = (
            target_date.replace(tzinfo=None) if target_date.tzinfo else target_date
        )
        self.current_time = target_date_naive.replace(hour=9, minute=15, second=0)
        self.end_time = target_date_naive.replace(hour=15, minute=25, second=0)
        self.trades = []
        self.positions = []
        self.current_capital = initial_capital

        # Store historical data for all stocks
        self.historical_data = {}
        self.stock_to_instrument_token = {}

        # Track statistics
        self.total_signals = 0
        self.total_entries = 0
        self.total_exits = 0

    def run_simulation(self) -> Dict[str, Any]:
        """Run full day simulation."""
        logger.info(
            f"🚀 Starting simulation from {self.current_time} to {self.end_time}"
        )

        # Step 1: Initialize - fetch instrument tokens and historical data
        if not self._initialize_data():
            logger.error("❌ Failed to initialize data. Cannot run simulation.")
            return self._get_empty_results()

        # Step 2: Simulate time progression
        execution_start = datetime.now()
        self._simulate_time_progression()
        execution_time = (datetime.now() - execution_start).total_seconds()

        # Step 3: Close all remaining positions at end of day
        self._close_all_positions()

        # Step 4: Calculate performance
        performance = self._calculate_performance()

        return {
            "date": self.target_date.strftime("%Y-%m-%d"),
            "execution_time": f"{execution_time:.2f} seconds",
            "stocks_simulated": len(self.stock_list),
            "total_signals": self.total_signals,
            "total_entries": self.total_entries,
            "total_exits": self.total_exits,
            "trades": self.trades,
            "positions": self.positions,
            "performance": performance,
        }

    def _initialize_data(self) -> bool:
        """Fetch instrument tokens and historical data for all stocks."""
        logger.info("📊 Initializing historical data...")

        # Get instrument tokens
        for stock in self.stock_list:
            try:
                instrument_token = self.mock_kite.get_instrument_token("NSE", stock)
                if instrument_token:
                    self.stock_to_instrument_token[stock] = instrument_token
                    logger.info(f"  ✅ {stock}: {instrument_token}")
                else:
                    logger.warning(f"  ⚠️  Could not find instrument token for {stock}")
                    return False
            except Exception as e:
                logger.error(f"  ❌ Error getting instrument token for {stock}: {e}")
                return False

        # Fetch historical data (60 days + target day for indicators)
        # Ensure dates are timezone-naive
        target_date_naive = (
            self.target_date.replace(tzinfo=None)
            if self.target_date.tzinfo
            else self.target_date
        )
        from_date = target_date_naive - timedelta(days=60)
        to_date = target_date_naive + timedelta(days=1)  # Include target day

        for stock, instrument_token in self.stock_to_instrument_token.items():
            try:
                logger.info(f"  📈 Fetching historical data for {stock}...")
                historical_data = self.mock_kite.get_historical_data(
                    instrument_token=instrument_token,
                    from_date=from_date,
                    to_date=to_date,
                    interval="5minute",
                )

                if historical_data:
                    # Convert to list of dicts with consistent format
                    candles = []
                    for candle in historical_data:
                        # Kite API returns candles with 'date' or 'timestamp' key
                        timestamp = candle.get("date") or candle.get("timestamp")
                        if isinstance(timestamp, str):
                            timestamp = pd.to_datetime(timestamp)
                        elif not isinstance(timestamp, datetime):
                            timestamp = pd.to_datetime(timestamp)

                        # Normalize to timezone-naive datetime
                        if hasattr(timestamp, "tz_localize"):
                            # pandas Timestamp
                            if timestamp.tz is not None:
                                timestamp = timestamp.tz_localize(None)
                        elif (
                            hasattr(timestamp, "tzinfo")
                            and timestamp.tzinfo is not None
                        ):
                            # datetime with timezone
                            timestamp = timestamp.replace(tzinfo=None)

                        # Convert to datetime if it's a pandas Timestamp
                        if hasattr(timestamp, "to_pydatetime"):
                            timestamp = timestamp.to_pydatetime()

                        candles.append(
                            {
                                "timestamp": timestamp,
                                "open": float(candle.get("open", 0)),
                                "high": float(candle.get("high", 0)),
                                "low": float(candle.get("low", 0)),
                                "close": float(candle.get("close", 0)),
                                "volume": int(candle.get("volume", 0)),
                            }
                        )

                    self.historical_data[stock] = sorted(
                        candles, key=lambda x: x["timestamp"]
                    )
                    logger.info(
                        f"    ✅ Loaded {len(self.historical_data[stock])} candles"
                    )
                else:
                    logger.warning(f"    ⚠️  No historical data for {stock}")
                    return False

            except Exception as e:
                logger.error(f"    ❌ Error fetching data for {stock}: {e}")
                return False

        logger.info("✅ Data initialization complete")
        return True

    def _simulate_time_progression(self):
        """Simulate time from 9:15 AM to 3:25 PM in 5-minute intervals."""
        current = self.current_time

        while current <= self.end_time:
            # Process exits first for all stocks (to free up position slots)
            # This ensures position limit is respected correctly
            for stock in self.stock_list:
                self._process_exits_at_time(stock, current)

            # Then process entries for all stocks (using updated position count)
            for stock in self.stock_list:
                self._process_entries_at_time(stock, current)

            # Move to next 5-minute interval
            current += timedelta(minutes=5)

    def _get_indicators_for_stock(self, stock: str, current_time: datetime) -> Dict:
        """Get indicators for a stock at a specific time."""
        try:
            # Ensure current_time is timezone-naive for comparison
            if current_time.tzinfo is not None:
                current_time = current_time.replace(tzinfo=None)

            relevant_candles = []
            for c in self.historical_data.get(stock, []):
                candle_timestamp = c["timestamp"]
                # Ensure candle timestamp is timezone-naive
                if isinstance(candle_timestamp, str):
                    candle_timestamp = pd.to_datetime(candle_timestamp)
                if (
                    hasattr(candle_timestamp, "tz_localize")
                    and candle_timestamp.tz is not None
                ):
                    candle_timestamp = candle_timestamp.tz_localize(None)
                elif (
                    hasattr(candle_timestamp, "tzinfo")
                    and candle_timestamp.tzinfo is not None
                ):
                    candle_timestamp = candle_timestamp.replace(tzinfo=None)
                if hasattr(candle_timestamp, "to_pydatetime"):
                    candle_timestamp = candle_timestamp.to_pydatetime()

                if candle_timestamp <= current_time:
                    relevant_candles.append(c)

            if len(relevant_candles) < 52:  # Need at least 52 for Ichimoku
                return None

            # Convert to DataFrame
            df = pd.DataFrame(relevant_candles)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()

            # Ensure we have required columns
            if not all(col in df.columns for col in ["open", "high", "low", "close"]):
                return None

            if "volume" not in df.columns:
                df["volume"] = 0

            # Calculate indicators
            indicators = self.technical_analyzer.get_indicators(df)
            return indicators

        except Exception as e:
            logger.error(
                f"❌ Error getting indicators for {stock} at {current_time}: {e}"
            )
            return None

    def _process_exits_at_time(self, stock: str, current_time: datetime):
        """Process exits for a stock at a specific time."""
        try:
            indicators = self._get_indicators_for_stock(stock, current_time)
            if not indicators:
                return

            # Check existing positions for this stock (up to 6 positions per stock allowed)
            active_positions_for_stock = [
                p
                for p in self.positions
                if p["stock"] == stock and p["status"] == "ACTIVE"
            ]

            # Check exit signals for the active position of this stock
            for position in active_positions_for_stock:
                self._check_exit(stock, indicators, position, current_time)

        except Exception as e:
            logger.error(
                f"❌ Error processing exits for {stock} at {current_time}: {e}"
            )

    def _process_entries_at_time(self, stock: str, current_time: datetime):
        """Process entries for a stock at a specific time."""
        try:
            indicators = self._get_indicators_for_stock(stock, current_time)
            if not indicators:
                return

            # Allow up to 6 positions per stock
            # But still respect overall MAX_POSITIONS limit
            self._check_entry(stock, indicators, current_time)

        except Exception as e:
            logger.error(
                f"❌ Error processing entries for {stock} at {current_time}: {e}"
            )

    def _check_entry(self, stock: str, indicators: Dict, current_time: datetime):
        """Check for entry signals."""
        try:
            # Check if stock already has maximum allowed positions (up to 6 positions per stock)
            active_positions_for_stock = [
                p
                for p in self.positions
                if p["stock"] == stock and p["status"] == "ACTIVE"
            ]
            max_positions_per_stock = 6
            if len(active_positions_for_stock) >= max_positions_per_stock:
                # Stock already has maximum positions, skip entry
                return

            # Check risk limits (total portfolio position limit)
            active_positions = [p for p in self.positions if p["status"] == "ACTIVE"]
            if not self.risk_manager.should_trade(
                len(active_positions),
                portfolio_pnl=0.0,
                initial_capital=self.initial_capital,
            ):
                return

            # Generate entry signal
            entry_signal = self.signal_generator.generate_entry_signal(indicators)

            if entry_signal:
                self.total_signals += 1
                current_price = indicators.get("ichimoku", {}).get("current_price")
                if not current_price:
                    return

                # Calculate position size (equal allocation across all stocks)
                # For simulation, allocate equal capital per stock (up to 9 stocks max)
                max_stocks = max(len(self.stock_list), 9)
                position_size = self.initial_capital / max_stocks
                quantity = int(position_size / current_price)

                if quantity <= 0:
                    return

                # Calculate SL/TP using position manager methods
                stop_loss = self.position_manager.calculate_stop_loss(current_price)
                take_profit = self.position_manager.calculate_take_profit(current_price)

                # Create position
                position = {
                    "stock": stock,
                    "entry_price": current_price,
                    "quantity": quantity,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "entry_time": current_time,
                    "status": "ACTIVE",
                }

                self.positions.append(position)
                self.total_entries += 1

                # Record trade
                trade = {
                    "timestamp": current_time,
                    "stock": stock,
                    "action": "BUY",
                    "price": current_price,
                    "quantity": quantity,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "signal": entry_signal.get("reason", ""),
                    "pnl": None,
                    "pnl_percent": None,
                    "exit_reason": None,
                }
                self.trades.append(trade)

                logger.info(
                    f"📈 Entry: {stock} @ ₹{current_price:.2f} x {quantity} at {current_time.strftime('%H:%M')}"
                )

        except Exception as e:
            logger.error(f"❌ Error checking entry for {stock}: {e}")

    def _check_exit(
        self, stock: str, indicators: Dict, position: Dict, current_time: datetime
    ):
        """Check for exit signals."""
        try:
            current_price = indicators.get("ichimoku", {}).get("current_price")
            if not current_price:
                return

            # Check exit conditions
            exit_reason = None

            # Check stop-loss
            if current_price <= position["stop_loss"]:
                exit_reason = "STOP_LOSS"
            # Check take-profit
            elif current_price >= position["take_profit"]:
                exit_reason = "TAKE_PROFIT"
            # Check technical exit
            else:
                exit_signal = self.signal_generator.generate_exit_signal(
                    indicators,
                    {
                        "stop_loss": position["stop_loss"],
                        "take_profit": position["take_profit"],
                        "entry_price": position["entry_price"],
                    },
                )
                if exit_signal:
                    exit_reason = exit_signal.get("reason", "TECHNICAL_REVERSAL")

            if exit_reason:
                # Calculate P&L
                pnl = (current_price - position["entry_price"]) * position["quantity"]
                pnl_percent = (
                    (current_price - position["entry_price"]) / position["entry_price"]
                ) * 100

                # Update position
                position["exit_price"] = current_price
                position["exit_time"] = current_time
                position["pnl"] = pnl
                position["pnl_percent"] = pnl_percent
                position["exit_reason"] = exit_reason
                position["status"] = "CLOSED"

                self.total_exits += 1

                # Record trade
                trade = {
                    "timestamp": current_time,
                    "stock": stock,
                    "action": "SELL",
                    "price": current_price,
                    "quantity": position["quantity"],
                    "stop_loss": position["stop_loss"],
                    "take_profit": position["take_profit"],
                    "pnl": pnl,
                    "pnl_percent": pnl_percent,
                    "exit_reason": exit_reason,
                    "signal": None,
                }
                self.trades.append(trade)

                logger.info(
                    f"📉 Exit: {stock} @ ₹{current_price:.2f} - P&L: ₹{pnl:.2f} ({pnl_percent:.2f}%) - {exit_reason}"
                )

        except Exception as e:
            logger.error(f"❌ Error checking exit for {stock}: {e}")

    def _close_all_positions(self):
        """Close all remaining positions at end of day."""
        active_positions = [p for p in self.positions if p["status"] == "ACTIVE"]

        # Ensure end_time is timezone-naive
        end_time = self.end_time
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        for position in active_positions:
            # Get last available price from historical data
            stock_candles = self.historical_data.get(position["stock"], [])
            if not stock_candles:
                exit_price = position["entry_price"]  # Fallback
            else:
                # Get last candle before or at end time
                valid_candles = []
                for c in stock_candles:
                    candle_timestamp = c["timestamp"]
                    # Normalize timestamp
                    if isinstance(candle_timestamp, str):
                        candle_timestamp = pd.to_datetime(candle_timestamp)
                    if (
                        hasattr(candle_timestamp, "tz_localize")
                        and candle_timestamp.tz is not None
                    ):
                        candle_timestamp = candle_timestamp.tz_localize(None)
                    elif (
                        hasattr(candle_timestamp, "tzinfo")
                        and candle_timestamp.tzinfo is not None
                    ):
                        candle_timestamp = candle_timestamp.replace(tzinfo=None)

                    if candle_timestamp <= end_time:
                        valid_candles.append(c)

                if valid_candles:
                    last_candle = max(valid_candles, key=lambda x: x["timestamp"])
                    exit_price = last_candle["close"]
                else:
                    exit_price = position["entry_price"]

            pnl = (exit_price - position["entry_price"]) * position["quantity"]
            pnl_percent = (
                (exit_price - position["entry_price"]) / position["entry_price"]
            ) * 100

            position["exit_price"] = exit_price
            position["exit_time"] = self.end_time
            position["pnl"] = pnl
            position["pnl_percent"] = pnl_percent
            position["exit_reason"] = "EOD"
            position["status"] = "CLOSED"

            self.total_exits += 1

            trade = {
                "timestamp": self.end_time,
                "stock": position["stock"],
                "action": "SELL",
                "price": exit_price,
                "quantity": position["quantity"],
                "stop_loss": position["stop_loss"],
                "take_profit": position["take_profit"],
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "exit_reason": "EOD",
                "signal": None,
            }
            self.trades.append(trade)

    def _calculate_performance(self) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        closed_positions = [p for p in self.positions if p["status"] == "CLOSED"]

        if not closed_positions:
            return {
                "date": self.target_date.strftime("%Y-%m-%d"),
                "total_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "max_drawdown": 0.0,
                "initial_capital": self.initial_capital,
                "final_capital": self.initial_capital,
            }

        total_pnl = sum(p["pnl"] for p in closed_positions)
        winning_trades = sum(1 for p in closed_positions if p["pnl"] > 0)
        losing_trades = len(closed_positions) - winning_trades

        win_rate = (
            (winning_trades / len(closed_positions)) * 100 if closed_positions else 0
        )

        # Calculate max drawdown
        cumulative_pnl = 0
        max_drawdown = 0
        peak = 0

        for pos in sorted(closed_positions, key=lambda x: x["exit_time"]):
            cumulative_pnl += pos["pnl"]
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        final_capital = self.initial_capital + total_pnl

        return {
            "date": self.target_date.strftime("%Y-%m-%d"),
            "total_trades": len(closed_positions),
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "max_drawdown": max_drawdown,
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
        }

    def _get_empty_results(self) -> Dict[str, Any]:
        """Return empty results structure on failure."""
        return {
            "date": self.target_date.strftime("%Y-%m-%d"),
            "execution_time": "0 seconds",
            "stocks_simulated": 0,
            "total_signals": 0,
            "total_entries": 0,
            "total_exits": 0,
            "trades": [],
            "positions": [],
            "performance": {
                "total_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
            },
        }
