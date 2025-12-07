# app/domains/market/watchlist_manager.py
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from app.shared.logger import logger


class WatchlistManager:
    """Manages watchlist storage and retrieval"""

    def __init__(self):
        self.storage_dir = Path("storage/watchlists")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_watchlist(
        self,
        watchlist: Dict[str, List[str]],
        sectors: List[str],
        prediction: dict,
    ) -> str:
        """Save watchlist with metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{self.storage_dir}/watchlist_{timestamp}.json"

        data = {
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_sentiment": {
                "sentiment": prediction.get("sentiment"),
                "confidence": prediction.get("confidence"),
            },
            "selected_sectors": sectors,
            "watchlist": watchlist,
            "total_stocks": sum(len(stocks) for stocks in watchlist.values()),
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"📋 Watchlist saved: {filename}")
        return filename

    def get_latest_watchlist(self) -> Optional[Dict]:
        """Get the most recent watchlist"""
        watchlists = sorted(
            self.storage_dir.glob("watchlist_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if watchlists:
            with open(watchlists[0], "r") as f:
                return json.load(f)
        return None





