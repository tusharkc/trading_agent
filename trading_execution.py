"""
Standalone script for running trading execution phase.
"""
import sys
from app.domains.trading.execution_engine import ExecutionEngine
from app.shared.config import config
from app.shared.logger import logger


def main():
    """Main function for trading execution."""
    try:
        # Validate configuration
        if not config.TRADING_ENABLED:
            logger.info("⚠️  Trading is not enabled. Set TRADING_ENABLED=true in .env")
            return 1

        # Initialize execution engine (will fetch capital from account automatically)
        logger.info("🚀 Starting Trading Execution Engine...")
        engine = ExecutionEngine(initial_capital=None)  # None = fetch from account

        # Start monitoring
        engine.start_monitoring()

        return 0

    except KeyboardInterrupt:
        logger.info("\n🛑 Trading execution interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Trading execution error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

