"""
Orchestrator combining Telegram bot and Trading Engine.
"""
import asyncio
import threading
import time
from pathlib import Path
from telegram_bot import TelegramBot
from app.domains.trading.execution_engine import ExecutionEngine
from app.shared.config import config
from app.shared.logger import logger


class BotOrchestrator:
    """Orchestrator that combines Telegram bot and Trading Engine."""

    def __init__(self):
        self.trading_engine = None
        self.telegram_bot = None
        self.telegram_thread = None

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            Path("logs"),
            Path("storage/watchlists"),
            Path("storage/sentiment_data"),
            Path("storage/simulations"),
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Start both Telegram bot and Trading Engine"""
        try:
            # Ensure all required directories exist before starting
            self._ensure_directories()
            
            logger.info("🚀 Starting Bot Orchestrator...")

            # Initialize trading engine (only if trading is enabled)
            if config.TRADING_ENABLED:
                logger.info("💰 Initializing Trading Engine...")
                self.trading_engine = ExecutionEngine(initial_capital=None)
            else:
                logger.warning("⚠️  Trading is disabled. Set TRADING_ENABLED=true to enable trading.")
                self.trading_engine = None

            # Initialize Telegram bot with trading engine reference
            logger.info("🤖 Initializing Telegram Bot...")
            self.telegram_bot = TelegramBot(trading_engine=self.trading_engine)

            # Run Telegram bot in separate thread
            self.telegram_thread = threading.Thread(
                target=self.telegram_bot.run,
                daemon=True,
                name="TelegramBot"
            )
            self.telegram_thread.start()
            logger.info("✅ Telegram bot thread started")

            # Send startup notification (with delay to ensure bot is ready)
            def send_startup_notification():
                time.sleep(2)  # Wait for bot to initialize
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.telegram_bot.send_notification(
                            "🤖 *Trading Bot Started*\n\n"
                            "Bot is now running and ready to receive commands.\n"
                            "Use /help to see available commands."
                        )
                    )
                    loop.close()
                except Exception as e:
                    logger.warning(f"Could not send startup notification: {e}")
            
            startup_thread = threading.Thread(target=send_startup_notification, daemon=True)
            startup_thread.start()

            # Keep main thread alive
            try:
                while True:
                    time.sleep(1)
                    # Check if Telegram thread is still alive
                    if not self.telegram_thread.is_alive():
                        logger.error("❌ Telegram bot thread died")
                        break
            except KeyboardInterrupt:
                logger.info("\n🛑 Received interrupt signal")
                self.stop()

        except Exception as e:
            logger.error(f"❌ Error in orchestrator: {e}")
            import traceback
            traceback.print_exc()
            self.stop()

    def stop(self):
        """Stop both services"""
        logger.info("🛑 Stopping Bot Orchestrator...")
        
        # Stop trading engine
        if self.trading_engine and self.trading_engine.is_running:
            self.trading_engine.stop_monitoring()
            logger.info("✅ Trading engine stopped")

        # Send shutdown notification
        if self.telegram_bot:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.telegram_bot.send_notification(
                        "🛑 *Trading Bot Stopped*\n\nBot is shutting down."
                    )
                )
                loop.close()
            except:
                pass

        logger.info("✅ Bot Orchestrator stopped")


if __name__ == "__main__":
    orchestrator = BotOrchestrator()
    orchestrator.start()

