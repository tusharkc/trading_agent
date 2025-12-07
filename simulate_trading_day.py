"""
Simulate a full trading day using historical data.
Runs the complete workflow: stock selection -> trading execution.
Logs all trades to CSV.
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import List

from app.domains.trading.simulation.simulator import TradingSimulator
from app.domains.trading.simulation.csv_logger import CSVLogger
from app.shared.logger import logger


def parse_stocks(stocks_input: str) -> List[str]:
    """
    Parse stock list from comma-separated string or file.

    Args:
        stocks_input: Comma-separated stocks or path to file

    Returns:
        List of stock symbols
    """
    # Check if it's a file path
    if Path(stocks_input).exists():
        with open(stocks_input, "r") as f:
            stocks = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
        return stocks

    # Parse comma-separated list
    stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]
    return stocks


def main():
    """Main function for simulation."""
    parser = argparse.ArgumentParser(
        description="Simulate trading day using historical data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulate with manual stock list
  python simulate_trading_day.py --date 2025-12-07 --stocks RELIANCE,TCS,INFY

  # With custom capital
  python simulate_trading_day.py --date 2025-12-07 --stocks RELIANCE,TCS,INFY --capital 100000

  # From file
  python simulate_trading_day.py --date 2025-12-07 --stocks stocks.txt
        """,
    )

    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Date to simulate (YYYY-MM-DD format, e.g., 2025-12-07)",
    )

    parser.add_argument(
        "--stocks",
        type=str,
        required=True,
        help="Comma-separated stock list or path to file with one stock per line",
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=100000.0,
        help="Initial capital in rupees (default: 100000)",
    )

    args = parser.parse_args()

    try:
        # Parse date
        target_date = datetime.strptime(args.date, "%Y-%m-%d")

        # Parse stocks
        stock_list = parse_stocks(args.stocks)

        if not stock_list:
            print("❌ Error: No stocks provided")
            return 1

        logger.info(f"🎮 Starting simulation for {args.date}")
        logger.info("=" * 60)

        logger.info(f"📋 Stocks to simulate: {', '.join(stock_list)}")
        logger.info(f"💰 Initial capital: ₹{args.capital:,.2f}")
        logger.info(f"📅 Target date: {target_date.strftime('%Y-%m-%d')}")

        # Initialize simulator
        simulator = TradingSimulator(
            target_date=target_date,
            initial_capital=args.capital,
            stock_list=stock_list,
        )

        # Run simulation
        logger.info(f"\n🔄 Running simulation...")
        logger.info("-" * 60)
        results = simulator.run_simulation()

        # Initialize CSV logger
        csv_logger = CSVLogger(target_date=target_date)

        # Log results to CSV
        logger.info("\n📊 Generating CSV reports...")
        csv_logger.log_trades(results.get("trades", []))
        csv_logger.log_positions(results.get("positions", []))
        csv_logger.log_performance(results.get("performance", {}))
        csv_logger.log_simulation_summary(results)

        # Print summary
        print("\n" + "=" * 60)
        print("📊 SIMULATION SUMMARY")
        print("=" * 60)
        perf = results.get("performance", {})
        print(f"Date: {results.get('date')}")
        print(f"Stocks Simulated: {results.get('stocks_simulated')}")
        print(
            f"Total Trades: {results.get('total_entries', 0) + results.get('total_exits', 0)}"
        )
        print(f"  - Entries: {results.get('total_entries', 0)}")
        print(f"  - Exits: {results.get('total_exits', 0)}")
        print(f"Total P&L: ₹{perf.get('total_pnl', 0):,.2f}")
        print(f"Win Rate: {perf.get('win_rate', 0):.2f}%")
        print(f"Winning Trades: {perf.get('winning_trades', 0)}")
        print(f"Losing Trades: {perf.get('losing_trades', 0)}")
        print(f"Initial Capital: ₹{perf.get('initial_capital', 0):,.2f}")
        print(f"Final Capital: ₹{perf.get('final_capital', 0):,.2f}")
        print(f"Max Drawdown: ₹{perf.get('max_drawdown', 0):,.2f}")
        print(f"\n✅ CSV Logs saved to: {csv_logger.get_output_dir()}")
        print("=" * 60)

        return 0

    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        print("   Date must be in YYYY-MM-DD format (e.g., 2025-12-07)")
        return 1
    except Exception as e:
        logger.error(f"❌ Simulation error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
