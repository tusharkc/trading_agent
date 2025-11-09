from alpha_vantage.timeseries import TimeSeries
from nsepython import index_history
from app.shared.config import config
from app.shared.logger import logger
from datetime import datetime, timedelta
import pandas as pd


class MarketDataFetcher:
    def __init__(self):
        self.ts = TimeSeries(key=config.ALPHA_VANTAGE_API_KEY, output_format="json")

    def fetch_indian_market_data(self, symbol="NIFTY 50", days=30):
        """
        Fetches historical daily data for Indian market indices (e.g., NIFTY 50).
        """
        logger.info(
            f"📈 Fetching Indian market data for {symbol} for last {days} days..."
        )
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # index_history requires dates in 'dd-Mon-yyyy' format
            data = index_history(
                symbol, start_date.strftime("%d-%b-%Y"), end_date.strftime("%d-%b-%Y")
            )

            if data.empty:
                logger.error(f"❌ Failed to fetch data for {symbol} from nsepython.")
                return []

            # Convert to list of dictionaries
            data = data.to_dict("records")

            filtered_data = []
            for record in data:
                filtered_data.append(
                    {
                        "date": record["HistoricalDate"],
                        "open": record["OPEN"],
                        "high": record["HIGH"],
                        "low": record["LOW"],
                        "close": record["CLOSE"],
                        "volume": record.get("Volume", 0),
                    }
                )

            filtered_data.sort(key=lambda x: x["date"])
            logger.info(
                f"✅ Fetched {len(filtered_data)} days of Indian market data for {symbol}."
            )
            return filtered_data
        except Exception as e:
            logger.error(f"❌ Error fetching Indian market data for {symbol}: {e}")
            return []

    def fetch_us_market_data(self, symbol="SPY", days=30):
        """
        Fetches historical daily data for US market indices (e.g., S&P 500 via SPY ETF).
        """
        logger.info(f"📈 Fetching US market data for {symbol} for last {days} days...")
        try:
            data, meta_data = self.ts.get_daily(symbol=symbol, outputsize="full")

            # Filter for the last 'days'
            filtered_data = []
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            for date_str, values in data.items():
                current_data_date = datetime.strptime(date_str, "%Y-%m-%d")
                if start_date <= current_data_date <= end_date:
                    filtered_data.append(
                        {
                            "date": date_str,
                            "open": float(values["1. open"]),
                            "high": float(values["2. high"]),
                            "low": float(values["3. low"]),
                            "close": float(values["4. close"]),
                            "volume": int(values["5. volume"]),
                        }
                    )

            filtered_data.sort(key=lambda x: x["date"])
            logger.info(
                f"✅ Fetched {len(filtered_data)} days of US market data for {symbol}."
            )
            return filtered_data
        except Exception as e:
            logger.error(f"❌ Error fetching US market data for {symbol}: {e}")
            return []
