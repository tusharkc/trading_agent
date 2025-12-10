"""
Telegram bot for controlling trading bot.
"""

import asyncio
import os
from datetime import datetime, date
from typing import List
from pathlib import Path
from urllib.parse import urlparse
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from app.shared.config import config
from app.shared.logger import logger
from app.domains.trading.models.performance import Performance
from app.domains.trading.models.db import get_session


class TelegramBot:
    """Telegram bot handler for trading bot control."""

    def __init__(self, trading_engine=None):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.trading_engine = trading_engine
        self.application = None
        self.bot_instance = None
        self.project_root = Path(__file__).resolve().parent

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        await update.message.reply_text(
            "🤖 *Trading Bot Started!*\n\nUse /help to see available commands",
            parse_mode="Markdown",
        )
        # Start trading engine if not already running
        if self.trading_engine and not self.trading_engine.is_running:
            try:
                self.trading_engine.start_monitoring()
                await update.message.reply_text("✅ Trading engine started")
            except Exception as e:
                await update.message.reply_text(f"❌ Error starting engine: {e}")

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        if self.trading_engine and self.trading_engine.is_running:
            self.trading_engine.stop_monitoring()
            await update.message.reply_text("🛑 Trading Bot Stopped")
        else:
            await update.message.reply_text("⚠️ Bot is not running")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        status = self.get_bot_status()
        await update.message.reply_text(status, parse_mode="Markdown")

    async def positions_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /positions command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        positions = self.get_positions()
        await update.message.reply_text(positions, parse_mode="Markdown")

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        balance = self.get_balance()
        await update.message.reply_text(balance, parse_mode="Markdown")

    async def performance_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /performance command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        performance = self.get_performance()
        await update.message.reply_text(performance, parse_mode="Markdown")

    async def watchlist_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /watchlist command"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        watchlist = self.get_watchlist()
        await update.message.reply_text(watchlist, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - No authorization required"""
        try:
            help_text = """
🤖 *Trading Bot Commands*

/start - Start trading bot
/stop - Stop trading bot
/status - Get current bot status
/positions - List all active positions
/balance - Check account balance
/performance - Today's performance summary
/watchlist - Show current watchlist
/help - Show this help message
            """
            await update.message.reply_text(help_text.strip(), parse_mode="Markdown")
            logger.info(f"Help command received from user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"❌ Error handling help command: {e}")
            try:
                await update.message.reply_text(
                    "❌ Error processing help command. Please try again."
                )
            except Exception:
                logger.error("❌ Failed to send error message for help command")

    def _is_authorized(self, update: Update) -> bool:
        """Check if user is authorized"""
        user_id = str(update.effective_user.id)
        return user_id == self.chat_id

    def get_bot_status(self) -> str:
        """Get current bot status"""
        try:
            if not self.trading_engine:
                return "❌ Trading engine not initialized"

            is_running = self.trading_engine.is_running
            status_emoji = "🟢" if is_running else "🔴"

            active_positions = []
            if self.trading_engine.position_manager:
                active_positions = (
                    self.trading_engine.position_manager.get_active_positions()
                )

            status = f"""
{status_emoji} *Bot Status*

*Status:* {"Running" if is_running else "Stopped"}
*Active Positions:* {len(active_positions)}
*Capital:* ₹{self.trading_engine.initial_capital:,.2f}
*Time:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")}
            """
            return status.strip()
        except Exception as e:
            return f"❌ Error getting status: {e}"

    def get_positions(self) -> str:
        """Get all active positions"""
        try:
            if not self.trading_engine or not self.trading_engine.position_manager:
                return "❌ Trading engine not initialized"

            positions = self.trading_engine.position_manager.get_active_positions()

            if not positions:
                return "📊 *No Active Positions*"

            position_text = "📊 *Active Positions*\n\n"
            total_pnl = 0

            for pos in positions:
                # Calculate current P&L (unrealized)
                # For simplicity, using entry price. In production, fetch current price
                pnl = pos.pnl if pos.pnl else 0
                pnl_percent = (
                    ((pnl / (pos.entry_price * pos.quantity)) * 100)
                    if pos.quantity > 0
                    else 0
                )
                pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"

                position_text += f"""
{pnl_emoji} *{pos.stock_symbol}*
Entry: ₹{pos.entry_price:.2f} x {pos.quantity}
SL: ₹{pos.stop_loss:.2f} | TP: ₹{pos.take_profit:.2f}
P&L: ₹{pnl:.2f} ({pnl_percent:+.2f}%)
                """
                total_pnl += pnl

            position_text += f"\n*Total P&L:* ₹{total_pnl:.2f}"
            return position_text.strip()
        except Exception as e:
            return f"❌ Error getting positions: {e}"

    def get_balance(self) -> str:
        """Get account balance"""
        try:
            if not self.trading_engine:
                return "❌ Trading engine not initialized"

            capital = self.trading_engine.initial_capital

            # Try to fetch current balance
            try:
                current_balance = (
                    self.trading_engine.kite_client.get_available_capital()
                )
            except Exception:
                current_balance = capital

            balance_text = f"""
💰 *Account Balance*

*Initial Capital:* ₹{capital:,.2f}
*Available Capital:* ₹{current_balance:,.2f}
*Time:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")}
            """
            return balance_text.strip()
        except Exception as e:
            return f"❌ Error getting balance: {e}"

    def get_performance(self) -> str:
        """Get today's performance"""
        try:
            session = get_session()
            today = date.today()

            performance = (
                session.query(Performance).filter(Performance.date == today).first()
            )

            if not performance:
                return "📈 *Performance*\n\nNo trades today yet"

            pnl_emoji = (
                "🟢"
                if performance.total_pnl > 0
                else "🔴"
                if performance.total_pnl < 0
                else "⚪"
            )

            performance_text = f"""
{pnl_emoji} *Today's Performance*

*Total Trades:* {performance.total_trades}
*Winning:* {performance.winning_trades} | *Losing:* {performance.losing_trades}
*Win Rate:* {performance.win_rate:.2f}%
*Total P&L:* ₹{performance.total_pnl:,.2f}
*Max Drawdown:* ₹{abs(performance.max_drawdown):,.2f}
*Consecutive Losses:* {performance.consecutive_losses}
            """
            return performance_text.strip()
        except Exception as e:
            return f"❌ Error getting performance: {e}"

    def get_watchlist(self) -> str:
        """Get current watchlist"""
        try:
            if not self.trading_engine or not self.trading_engine.watchlist_manager:
                return "❌ Trading engine not initialized"

            watchlist_data = (
                self.trading_engine.watchlist_manager.get_latest_watchlist()
            )

            if not watchlist_data:
                return "📋 *Watchlist*\n\nNo watchlist found"

            watchlist = watchlist_data.get("watchlist", {})
            sectors = watchlist_data.get("selected_sectors", [])
            sentiment = watchlist_data.get("market_sentiment", {})

            watchlist_text = f"""
📋 *Current Watchlist*

*Sentiment:* {sentiment.get("sentiment", "N/A")} ({sentiment.get("confidence", 0):.0f}%)
*Sectors:* {", ".join(sectors) if sectors else "N/A"}

*Stocks:*
            """

            total_stocks = 0
            for sector, stocks in watchlist.items():
                if stocks:
                    watchlist_text += f"\n*{sector}:*\n"
                    for stock in stocks:
                        watchlist_text += f"  • {stock}\n"
                    total_stocks += len(stocks)

            watchlist_text += f"\n*Total:* {total_stocks} stocks"
            return watchlist_text.strip()
        except Exception as e:
            return f"❌ Error getting watchlist: {e}"

    async def send_notification(self, message: str):
        """Send notification to Telegram"""
        try:
            if not self.bot_instance:
                self.bot_instance = Bot(token=self.bot_token)
            await self.bot_instance.send_message(
                chat_id=self.chat_id, text=message, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error sending Telegram notification: {e}")

    async def _tail_logs(self, lines: int = 50) -> str:
        """Return tail of latest log file."""
        try:
            log_dir = self.project_root.parent / "logs"
            if not log_dir.exists():
                return "❌ No logs directory found."
            log_files = sorted(
                log_dir.glob("bot_*.log"), key=lambda p: p.stat().st_mtime, reverse=True
            )
            if not log_files:
                return "❌ No log files found."
            latest = log_files[0]
            content = latest.read_text(errors="ignore").splitlines()
            tail = "\n".join(content[-lines:])
            return f"📜 Latest log ({latest.name}, last {lines} lines):\n{tail[-3500:]}"
        except Exception as e:
            return f"❌ Error reading logs: {e}"

    async def _run_subprocess(
        self,
        cmd: List[str],
        description: str,
        timeout: int = 300,
        cwd: Path = None,
    ) -> str:
        """
        Run a subprocess and return output (stdout/stderr).
        Args:
            cmd: Command list
            description: Human-readable description
            timeout: Max seconds to wait
            cwd: Working directory (defaults to project root)
        """
        try:
            workdir = cwd if cwd is not None else self.project_root.parent
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workdir),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return f"❌ {description} timed out after {timeout}s"

            output = stdout.decode().strip()
            errors = stderr.decode().strip()

            if proc.returncode != 0:
                combined = (output + "\n" + errors).strip()
                return f"❌ {description} failed (exit {proc.returncode}):\n{combined[-3500:]}"

            combined = (output + ("\n" + errors if errors else "")).strip()
            return (
                f"✅ {description} completed:\n{combined[-3500:]}"
                if combined
                else f"✅ {description} completed."
            )
        except Exception as e:
            logger.error(f"❌ Error running {description}: {e}")
            return f"❌ Error running {description}: {e}"

    async def run_analysis_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /run_analysis to execute main.py (analysis/watchlist generation)."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        await update.message.reply_text("⏳ Running analysis (main.py)...")
        main_path = self.project_root.parent / "main.py"
        result = await self._run_subprocess(
            ["python", str(main_path)],
            "Analysis (main.py)",
            timeout=600,
            cwd=self.project_root.parent,
        )
        await update.message.reply_text(result[:3900])

    async def backtest_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /backtest <YYYY-MM-DD> <STOCKS>"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return

        parts = update.message.text.split(maxsplit=2)
        if len(parts) < 3:
            await update.message.reply_text(
                "Usage: /backtest YYYY-MM-DD RELIANCE,TCS,INFY"
            )
            return

        date_str = parts[1]
        stocks = parts[2]

        await update.message.reply_text(
            f"⏳ Running backtest for {date_str} on {stocks} ..."
        )
        sim_path = self.project_root.parent / "simulate_trading_day.py"
        result = await self._run_subprocess(
            ["python", str(sim_path), "--date", date_str, "--stocks", stocks],
            f"Backtest {date_str}",
            timeout=900,
            cwd=self.project_root.parent,
        )
        await update.message.reply_text(result[:3900])

    async def check_token_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Validate Kite access token (uses refresh_token which just tests validity)."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        try:
            if not self.trading_engine:
                await update.message.reply_text("⚠️ Trading engine not initialized.")
                return
            ok = self.trading_engine.kite_client.refresh_token()
            if ok:
                await update.message.reply_text("✅ Kite access token is valid.")
            else:
                await update.message.reply_text(
                    "⚠️ Token validation failed. You may need to regenerate via generate_kite_token.py."
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Error checking token: {e}")

    async def start_trading_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start trading engine manually."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        if not self.trading_engine:
            await update.message.reply_text("⚠️ Trading engine not initialized.")
            return
        if self.trading_engine.is_running:
            await update.message.reply_text("ℹ️ Trading engine is already running.")
            return
        try:
            self.trading_engine.start_monitoring()
            await update.message.reply_text("✅ Trading engine started.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error starting trading engine: {e}")

    async def stop_trading_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Stop trading engine manually."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        if not self.trading_engine:
            await update.message.reply_text("⚠️ Trading engine not initialized.")
            return
        if not self.trading_engine.is_running:
            await update.message.reply_text("ℹ️ Trading engine is already stopped.")
            return
        try:
            self.trading_engine.stop_monitoring()
            await update.message.reply_text("✅ Trading engine stopped.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error stopping trading engine: {e}")

    async def set_position_size_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Set position size percent at runtime (not persisted). Usage: /set_position_size 15"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("Usage: /set_position_size 15")
            return
        try:
            val = float(parts[1])
            if val <= 0 or val > 100:
                raise ValueError("must be between 0 and 100")
            config.POSITION_SIZE_PERCENT = val
            await update.message.reply_text(
                f"✅ POSITION_SIZE_PERCENT set to {val}% (runtime only, not persisted)."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Invalid value: {e}")

    async def set_max_positions_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Set max positions at runtime (not persisted). Usage: /set_max_positions 9"""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("Usage: /set_max_positions 9")
            return
        try:
            val = int(parts[1])
            if val <= 0:
                raise ValueError("must be > 0")
            config.MAX_POSITIONS = val
            await update.message.reply_text(
                f"✅ MAX_POSITIONS set to {val} (runtime only, not persisted)."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Invalid value: {e}")

    async def clear_data_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Run clear_all_data.py to wipe DB/logs/watchlists/sentiment/simulations."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        await update.message.reply_text(
            "⚠️ Clearing data (DB, logs, watchlists, sentiment, simulations)..."
        )
        clear_path = self.project_root.parent / "clear_all_data.py"
        result = await self._run_subprocess(
            ["python", str(clear_path)],
            "Clear all data",
            timeout=120,
            cwd=self.project_root.parent,
        )
        await update.message.reply_text(result[:3900])

    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Return tail of latest log file."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized access")
            return
        tail = await self._tail_logs(lines=80)
        await update.message.reply_text(tail[:3900])

    def run(self):
        """Start Telegram bot"""
        try:
            if not self.bot_token:
                logger.error("❌ TELEGRAM_BOT_TOKEN not set")
                print("ERROR: TELEGRAM_BOT_TOKEN not set in environment variables")
                return

            if not self.chat_id:
                logger.error("❌ TELEGRAM_CHAT_ID not set")
                print("ERROR: TELEGRAM_CHAT_ID not set in environment variables")
                return

            logger.info(
                f"🤖 Initializing Telegram bot with token: {self.bot_token[:10]}..."
            )
            self.application = Application.builder().token(self.bot_token).build()

            # Register commands
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("stop", self.stop_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(
                CommandHandler("positions", self.positions_command)
            )
            self.application.add_handler(
                CommandHandler("balance", self.balance_command)
            )
            self.application.add_handler(
                CommandHandler("performance", self.performance_command)
            )
            self.application.add_handler(
                CommandHandler("watchlist", self.watchlist_command)
            )
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(
                CommandHandler("run_analysis", self.run_analysis_command)
            )
            self.application.add_handler(
                CommandHandler("backtest", self.backtest_command)
            )

            logger.info("🤖 Telegram bot started and ready to receive commands")
            print("✅ Telegram bot is running and ready!")

            # Start bot (blocking call) - MUST be in main thread for signal handlers
            # If WEBHOOK_URL is set, use webhook; otherwise fall back to polling.
            if config.WEBHOOK_URL:
                parsed = urlparse(config.WEBHOOK_URL)
                url_path = parsed.path.lstrip("/") or "telegram-webhook"
                port = int(os.getenv("PORT", "8080"))
                logger.info(
                    f"🤖 Starting Telegram bot via webhook on port {port}, path /{url_path}"
                )
                self.application.run_webhook(
                    listen="0.0.0.0",
                    port=port,
                    url_path=url_path,
                    webhook_url=config.WEBHOOK_URL,
                    secret_token=config.WEBHOOK_SECRET or None,
                    drop_pending_updates=True,
                )
            else:
                logger.info("🤖 Starting Telegram bot via polling...")
                self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"❌ Error running Telegram bot: {e}")
            print(f"ERROR: Telegram bot failed to start: {e}")
            import traceback

            traceback.print_exc()
            raise
