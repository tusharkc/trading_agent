# app/shared/config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Kite API credentials
    KITE_API_KEY = os.getenv("KITE_API_KEY")
    KITE_API_SECRET = os.getenv("KITE_API_SECRET")
    KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")

    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///storage/trading.db")

    # Trading configuration
    TRADING_ENABLED = os.getenv("TRADING_ENABLED", "false").lower() == "true"
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "9"))
    POSITION_SIZE_PERCENT = float(os.getenv("POSITION_SIZE_PERCENT", "11.11"))
    PLACE_SL_TP_ORDERS = os.getenv("PLACE_SL_TP_ORDERS", "false").lower() == "true"

    # Telegram configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

    @classmethod
    def validate(cls):
        if not cls.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is required")
        if not cls.NEWS_API_KEY:
            raise ValueError("NEWS_API_KEY is required")
        if cls.TRADING_ENABLED:
            if not cls.KITE_API_KEY:
                raise ValueError(
                    "KITE_API_KEY is required when TRADING_ENABLED is true"
                )
            if not cls.KITE_API_SECRET:
                raise ValueError(
                    "KITE_API_SECRET is required when TRADING_ENABLED is true"
                )
            if not cls.KITE_ACCESS_TOKEN:
                raise ValueError(
                    "KITE_ACCESS_TOKEN is required when TRADING_ENABLED is true"
                )
        return True


config = Config()
