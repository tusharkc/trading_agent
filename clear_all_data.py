#!/usr/bin/env python3
"""
Script to clear all trading bot data: database, logs, watchlists, and other storage.
This will start fresh for today.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def clear_database():
    """Clear the trading database."""
    db_path = Path("storage/trading.db")
    if db_path.exists():
        db_path.unlink()
        print(f"✅ Deleted database: {db_path}")
        return True
    else:
        print(f"ℹ️  Database not found: {db_path}")
        return False


def clear_logs():
    """Clear all log files."""
    logs_dir = Path("logs")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            for log_file in log_files:
                log_file.unlink()
                print(f"✅ Deleted log: {log_file}")
            return len(log_files)
        else:
            print("ℹ️  No log files found")
            return 0
    else:
        print("ℹ️  Logs directory not found")
        return 0


def clear_watchlists():
    """Clear all watchlist files."""
    watchlists_dir = Path("storage/watchlists")
    if watchlists_dir.exists():
        watchlist_files = list(watchlists_dir.glob("*.json"))
        if watchlist_files:
            for watchlist_file in watchlist_files:
                watchlist_file.unlink()
                print(f"✅ Deleted watchlist: {watchlist_file.name}")
            return len(watchlist_files)
        else:
            print("ℹ️  No watchlist files found")
            return 0
    else:
        print("ℹ️  Watchlists directory not found")
        return 0


def clear_sentiment_data():
    """Clear all sentiment prediction data."""
    sentiment_dir = Path("storage/sentiment_data")
    if sentiment_dir.exists():
        sentiment_files = list(sentiment_dir.glob("*.json"))
        if sentiment_files:
            for sentiment_file in sentiment_files:
                sentiment_file.unlink()
                print(f"✅ Deleted sentiment data: {sentiment_file.name}")
            return len(sentiment_files)
        else:
            print("ℹ️  No sentiment data files found")
            return 0
    else:
        print("ℹ️  Sentiment data directory not found")
        return 0


def clear_simulations():
    """Clear all simulation data."""
    simulations_dir = Path("storage/simulations")
    if simulations_dir.exists():
        simulation_dirs = [d for d in simulations_dir.iterdir() if d.is_dir()]
        if simulation_dirs:
            for sim_dir in simulation_dirs:
                shutil.rmtree(sim_dir)
                print(f"✅ Deleted simulation directory: {sim_dir.name}")
            return len(simulation_dirs)
        else:
            print("ℹ️  No simulation directories found")
            return 0
    else:
        print("ℹ️  Simulations directory not found")
        return 0


def main():
    """Main function to clear all data."""
    print("=" * 60)
    print("🧹 CLEARING ALL TRADING BOT DATA")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Confirm with user
    response = input("⚠️  This will delete ALL data. Are you sure? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled")
        return

    print()
    print("Starting cleanup...")
    print()

    # Clear all data
    db_deleted = clear_database()
    logs_deleted = clear_logs()
    watchlists_deleted = clear_watchlists()
    sentiment_deleted = clear_sentiment_data()
    simulations_deleted = clear_simulations()

    print()
    print("=" * 60)
    print("✅ CLEANUP COMPLETE")
    print("=" * 60)
    print(f"Database: {'Deleted' if db_deleted else 'Not found'}")
    print(f"Log files: {logs_deleted} deleted")
    print(f"Watchlist files: {watchlists_deleted} deleted")
    print(f"Sentiment data files: {sentiment_deleted} deleted")
    print(f"Simulation directories: {simulations_deleted} deleted")
    print()
    print(
        "🎯 You can now start fresh! Run 'python main.py' to generate a new watchlist."
    )
    print()


if __name__ == "__main__":
    main()

