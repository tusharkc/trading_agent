"""
CSV logger for simulation results.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class CSVLogger:
    """Logs simulation results to CSV files."""

    def __init__(self, target_date: datetime):
        """
        Initialize CSV logger.

        Args:
            target_date: The date being simulated
        """
        self.target_date = target_date
        self.output_dir = Path("storage/simulations") / target_date.strftime("%Y%m%d")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_output_dir(self) -> Path:
        """Get output directory path."""
        return self.output_dir

    def log_trades(self, trades: List[Dict]):
        """Log all trades to CSV."""
        if not trades:
            return

        csv_file = self.output_dir / "trades.csv"

        with open(csv_file, "w", newline="") as f:
            fieldnames = [
                "timestamp",
                "stock",
                "action",
                "price",
                "quantity",
                "stop_loss",
                "take_profit",
                "pnl",
                "pnl_percent",
                "signal",
                "exit_reason",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for trade in trades:
                writer.writerow(
                    {
                        "timestamp": trade.get("timestamp"),
                        "stock": trade.get("stock", ""),
                        "action": trade.get("action", ""),
                        "price": trade.get("price", ""),
                        "quantity": trade.get("quantity", ""),
                        "stop_loss": trade.get("stop_loss", ""),
                        "take_profit": trade.get("take_profit", ""),
                        "pnl": trade.get("pnl", ""),
                        "pnl_percent": trade.get("pnl_percent", ""),
                        "signal": trade.get("signal", ""),
                        "exit_reason": trade.get("exit_reason", ""),
                    }
                )

        print(f"✅ Trades logged to: {csv_file}")

    def log_positions(self, positions: List[Dict]):
        """Log all positions to CSV."""
        if not positions:
            return

        csv_file = self.output_dir / "positions.csv"

        with open(csv_file, "w", newline="") as f:
            fieldnames = [
                "stock",
                "entry_time",
                "exit_time",
                "entry_price",
                "exit_price",
                "quantity",
                "stop_loss",
                "take_profit",
                "pnl",
                "pnl_percent",
                "exit_reason",
                "status",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for pos in positions:
                writer.writerow(
                    {
                        "stock": pos.get("stock", ""),
                        "entry_time": pos.get("entry_time", ""),
                        "exit_time": pos.get("exit_time", ""),
                        "entry_price": pos.get("entry_price", ""),
                        "exit_price": pos.get("exit_price", ""),
                        "quantity": pos.get("quantity", ""),
                        "stop_loss": pos.get("stop_loss", ""),
                        "take_profit": pos.get("take_profit", ""),
                        "pnl": pos.get("pnl", ""),
                        "pnl_percent": pos.get("pnl_percent", ""),
                        "exit_reason": pos.get("exit_reason", ""),
                        "status": pos.get("status", ""),
                    }
                )

        print(f"✅ Positions logged to: {csv_file}")

    def log_performance(self, performance: Dict):
        """Log performance summary to CSV."""
        csv_file = self.output_dir / "performance.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=performance.keys())
            writer.writeheader()
            writer.writerow(performance)

        print(f"✅ Performance logged to: {csv_file}")

    def log_simulation_summary(self, results: Dict):
        """Log complete simulation results summary."""
        csv_file = self.output_dir / "simulation_summary.csv"

        summary = {
            "date": results.get("date", ""),
            "execution_time": results.get("execution_time", ""),
            "stocks_simulated": results.get("stocks_simulated", 0),
            "total_signals": results.get("total_signals", 0),
            "total_entries": results.get("total_entries", 0),
            "total_exits": results.get("total_exits", 0),
            "total_trades": len(results.get("trades", [])),
            "total_pnl": results.get("performance", {}).get("total_pnl", 0),
            "win_rate": results.get("performance", {}).get("win_rate", 0),
        }

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=summary.keys())
            writer.writeheader()
            writer.writerow(summary)

        print(f"✅ Simulation summary logged to: {csv_file}")
