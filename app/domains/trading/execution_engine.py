"""
Execution engine for coordinating all trading components.
"""
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from app.domains.trading.kite_client import KiteClient
from app.domains.trading.websocket_manager import WebSocketManager
from app.domains.trading.technical_analyzer import TechnicalAnalyzer
from app.domains.trading.signal_generator import SignalGenerator
from app.domains.trading.position_manager import PositionManager
from app.domains.trading.order_manager import OrderManager
from app.domains.trading.risk_manager import RiskManager
from app.domains.trading.models.position import PositionStatus
from app.domains.trading.models.db import init_db
from app.domains.market.watchlist_manager import WatchlistManager
from app.shared.config import config
from app.shared.logger import logger

# IST timezone
IST = timezone("Asia/Kolkata")


class ExecutionEngine:
    """Main execution engine coordinating all trading components."""

    def __init__(self, initial_capital: Optional[float] = None):
        """
        Initialize execution engine.
        Args:
            initial_capital: Optional initial capital (if provided, will override account balance).
                            If None, will fetch from account automatically.
        """
        # Initialize database first
        init_db()

        # Initialize components
        logger.info("🔧 Initializing execution engine components...")
        self.kite_client = KiteClient()
        
        # Always fetch capital from account (or use provided override)
        if initial_capital is not None:
            self.initial_capital = initial_capital
            logger.info(f"💰 Using provided capital override: ₹{self.initial_capital:,.2f}")
        else:
            logger.info("💰 Fetching available capital from Zerodha account...")
            try:
                self.initial_capital = self.kite_client.get_available_capital()
                logger.info(f"✅ Fetched available capital from account: ₹{self.initial_capital:,.2f}")
            except ValueError as e:
                logger.error(f"❌ Failed to fetch capital from account: {e}")
                logger.error("❌ Cannot start trading without valid account balance")
                raise
        self.websocket_manager = WebSocketManager(self.kite_client)
        self.technical_analyzer = TechnicalAnalyzer()
        self.signal_generator = SignalGenerator()
        self.position_manager = PositionManager()
        self.order_manager = OrderManager(self.kite_client)
        self.risk_manager = RiskManager()
        self.watchlist_manager = WatchlistManager()

        # Set up WebSocket candle callback
        self.websocket_manager.set_candle_close_callback(self._on_candle_close)

        # Watchlist data
        self.watchlist = {}
        self.stock_to_instrument_token = {}
        self.instrument_token_to_stock = {}

        # Historical data cache for indicators
        self.historical_data_cache = {}

        # Scheduler
        self.scheduler = BlockingScheduler(timezone=IST)
        self.is_running = False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("✅ Execution engine initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.stop_monitoring()

    def load_watchlist(self) -> bool:
        """Load watchlist from storage."""
        try:
            watchlist_data = self.watchlist_manager.get_latest_watchlist()
            if not watchlist_data:
                logger.error("❌ No watchlist found in storage")
                return False

            self.watchlist = watchlist_data.get("watchlist", {})
            logger.info(f"✅ Loaded watchlist: {sum(len(stocks) for stocks in self.watchlist.values())} stocks")

            # Get instrument tokens for all stocks
            self._initialize_instrument_tokens()
            return True

        except Exception as e:
            logger.error(f"❌ Error loading watchlist: {e}")
            return False

    def _initialize_instrument_tokens(self):
        """Get instrument tokens for all stocks in watchlist."""
        try:
            all_stocks = []
            for sector, stocks in self.watchlist.items():
                all_stocks.extend(stocks)

            logger.info(f"🔍 Fetching instrument tokens for {len(all_stocks)} stocks...")

            for stock_symbol in all_stocks:
                instrument_token = self.kite_client.get_instrument_token("NSE", stock_symbol)
                if instrument_token:
                    self.stock_to_instrument_token[stock_symbol] = instrument_token
                    self.instrument_token_to_stock[instrument_token] = stock_symbol
                    logger.info(f"  ✅ {stock_symbol}: {instrument_token}")
                else:
                    logger.warning(f"  ⚠️  Could not find instrument token for {stock_symbol}")

        except Exception as e:
            logger.error(f"❌ Error initializing instrument tokens: {e}")

    def initialize_indicators(self):
        """Fetch historical data and calculate initial indicators."""
        try:
            logger.info("📊 Initializing indicators with historical data...")

            # Get last 60 days of data for each stock
            from_date = datetime.now() - timedelta(days=60)
            to_date = datetime.now()

            for stock_symbol, instrument_token in self.stock_to_instrument_token.items():
                try:
                    logger.info(f"  📈 Fetching historical data for {stock_symbol}...")
                    historical_data = self.kite_client.get_historical_data(
                        instrument_token=instrument_token,
                        from_date=from_date,
                        to_date=to_date,
                        interval="5minute",
                    )

                    if historical_data:
                        self.historical_data_cache[stock_symbol] = historical_data
                        logger.info(f"    ✅ Fetched {len(historical_data)} candles")
                    else:
                        logger.warning(f"    ⚠️  No historical data for {stock_symbol}")

                except Exception as e:
                    logger.error(f"    ❌ Error fetching data for {stock_symbol}: {e}")

            logger.info("✅ Historical data initialization complete")

        except Exception as e:
            logger.error(f"❌ Error initializing indicators: {e}")

    def process_candle(self, instrument_token: int, candle: Dict[str, Any]):
        """Process a new 5-minute candle and check for signals."""
        try:
            stock_symbol = self.instrument_token_to_stock.get(instrument_token)
            if not stock_symbol:
                return

            logger.info(f"📊 Processing candle for {stock_symbol}...")

            # Update historical data cache
            if stock_symbol not in self.historical_data_cache:
                self.historical_data_cache[stock_symbol] = []
            self.historical_data_cache[stock_symbol].append(candle)

            # Keep only last 100 candles
            if len(self.historical_data_cache[stock_symbol]) > 100:
                self.historical_data_cache[stock_symbol] = self.historical_data_cache[stock_symbol][-100:]

            # Prepare DataFrame for indicators
            df = self.technical_analyzer.prepare_dataframe_from_candles(
                self.historical_data_cache[stock_symbol]
            )
            if df is None or len(df) < 52:
                logger.warning(f"⚠️  Insufficient data for {stock_symbol} indicators")
                return

            # Calculate indicators
            indicators = self.technical_analyzer.get_indicators(df)

            # Check for existing positions (can have multiple positions per stock, up to 6)
            positions = self.position_manager.get_positions_by_symbol(stock_symbol)

            if positions:
                # Check exit conditions for ALL positions of this stock
                for position in positions:
                    self._check_exit_signals(stock_symbol, indicators, position)
            
            # Always check entry conditions (as long as we haven't reached per-stock limit)
            self._check_entry_signals(stock_symbol, indicators)

        except Exception as e:
            logger.error(f"❌ Error processing candle for {instrument_token}: {e}")

    def _check_entry_signals(self, stock_symbol: str, indicators: Dict[str, Any]):
        """Check for entry signals."""
        try:
            # Check per-stock position limit (up to 6 positions per stock)
            active_positions_for_stock = self.position_manager.get_positions_by_symbol(stock_symbol)
            max_positions_per_stock = 6
            if len(active_positions_for_stock) >= max_positions_per_stock:
                logger.debug(f"  ⏳ Max positions ({max_positions_per_stock}) reached for {stock_symbol}")
                return

            # Check if trading is allowed (overall portfolio limit)
            active_positions = self.position_manager.get_active_positions()
            if not self.risk_manager.should_trade(
                len(active_positions),
                portfolio_pnl=0.0,  # Could calculate from active positions
                initial_capital=self.initial_capital,
            ):
                return

            # Generate entry signal
            entry_signal = self.signal_generator.generate_entry_signal(indicators)

            if entry_signal:
                logger.info(f"🎯 Entry signal detected for {stock_symbol}: {entry_signal['reason']}")
                self._execute_entry(stock_symbol, indicators)
            else:
                logger.debug(f"  ⏳ No entry signal for {stock_symbol}")

        except Exception as e:
            logger.error(f"❌ Error checking entry signals: {e}")

    def _check_exit_signals(self, stock_symbol: str, indicators: Dict[str, Any], position):
        """Check for exit signals."""
        try:
            exit_signal = self.signal_generator.generate_exit_signal(
                indicators,
                {
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "entry_price": position.entry_price,
                },
            )

            if exit_signal:
                logger.info(
                    f"🚪 Exit signal detected for {stock_symbol}: {exit_signal['reason']}"
                )
                self._execute_exit(stock_symbol, position, exit_signal["reason"])

        except Exception as e:
            logger.error(f"❌ Error checking exit signals: {e}")

    def _execute_entry(self, stock_symbol: str, indicators: Dict[str, Any]):
        """Execute entry trade."""
        try:
            current_price = indicators.get("ichimoku", {}).get("current_price")
            if not current_price:
                logger.error(f"❌ No current price available for {stock_symbol}")
                return

            # Calculate position size
            position_size = self.position_manager.calculate_position_size(self.initial_capital)
            quantity = int(position_size / current_price)

            if quantity <= 0:
                logger.warning(f"⚠️  Invalid quantity for {stock_symbol}: {quantity}")
                return

            # Calculate stop-loss and take-profit
            stop_loss = self.position_manager.calculate_stop_loss(current_price)
            take_profit = self.position_manager.calculate_take_profit(current_price)

            # Execute orders
            order_ids = self.order_manager.execute_entry(
                exchange="NSE",
                symbol=stock_symbol,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            if order_ids.get("buy_order"):
                # Create position record
                position = self.position_manager.create_position(
                    stock_symbol=stock_symbol,
                    entry_price=current_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
                logger.info(f"✅ Entry executed for {stock_symbol}")

        except Exception as e:
            logger.error(f"❌ Error executing entry: {e}")

    def _execute_exit(self, stock_symbol: str, position, exit_reason: str):
        """Execute exit trade."""
        try:
            # Get current price from latest indicator or quote
            quote = self.kite_client.get_quote([f"NSE:{stock_symbol}"])
            if not quote:
                logger.error(f"❌ Could not get quote for {stock_symbol}")
                return

            current_price = quote.get(f"NSE:{stock_symbol}", {}).get("last_price")
            if not current_price:
                logger.error(f"❌ No current price for {stock_symbol}")
                return

            # Execute exit
            # Note: In production, you'd track order IDs for SL/TP orders
            self.order_manager.execute_exit(
                exchange="NSE",
                symbol=stock_symbol,
                quantity=position.quantity,
                order_ids=[],  # Would contain SL/TP order IDs
            )

            # Close position
            self.position_manager.close_position(position.id, current_price, exit_reason)

            # Update performance
            pnl = position.pnl if hasattr(position, "pnl") else (current_price - position.entry_price) * position.quantity
            is_win = pnl > 0

            if not is_win:
                self.risk_manager.increment_consecutive_losses()
            else:
                self.risk_manager.reset_consecutive_losses()

        except Exception as e:
            logger.error(f"❌ Error executing exit: {e}")

    def _on_candle_close(self, instrument_token: int, candle: Dict[str, Any]):
        """Callback when a 5-minute candle closes."""
        self.process_candle(instrument_token, candle)

    def handle_end_of_day(self):
        """Square off all positions at end of day (3:25 PM)."""
        try:
            logger.info("🕐 End of day: Squaring off all positions...")
            active_positions = self.position_manager.get_active_positions()

            for position in active_positions:
                try:
                    self._execute_exit(position.stock_symbol, position, "EOD")
                except Exception as e:
                    logger.error(f"❌ Error closing position {position.stock_symbol}: {e}")

            logger.info(f"✅ Closed {len(active_positions)} positions at end of day")

        except Exception as e:
            logger.error(f"❌ Error in end-of-day procedure: {e}")

    def start_monitoring(self):
        """Start WebSocket and scheduler."""
        try:
            logger.info("🚀 Starting trading execution engine...")

            # Reset daily counters
            self.risk_manager.reset_daily_counters()

            # Load watchlist
            if not self.load_watchlist():
                logger.error("❌ Failed to load watchlist. Cannot start monitoring.")
                return

            # Initialize indicators
            self.initialize_indicators()

            # Connect WebSocket
            if not self.websocket_manager.connect():
                logger.error("❌ Failed to connect WebSocket. Cannot start monitoring.")
                return

            # Subscribe to all stocks
            instrument_tokens = list(self.stock_to_instrument_token.values())
            if instrument_tokens:
                self.websocket_manager.subscribe(instrument_tokens)

            # Schedule end-of-day at 3:25 PM IST
            self.scheduler.add_job(
                self.handle_end_of_day,
                CronTrigger(hour=15, minute=25, timezone=IST),
                id="end_of_day",
            )

            # Start scheduler
            self.is_running = True
            self.scheduler.start()

        except Exception as e:
            logger.error(f"❌ Error starting monitoring: {e}")
            self.stop_monitoring()

    def stop_monitoring(self):
        """Clean shutdown."""
        try:
            logger.info("🛑 Stopping trading execution engine...")
            self.is_running = False

            # Close WebSocket
            self.websocket_manager.disconnect()

            # Shutdown scheduler
            if self.scheduler.running:
                self.scheduler.shutdown()

            logger.info("✅ Execution engine stopped")

        except Exception as e:
            logger.error(f"❌ Error stopping monitoring: {e}")

