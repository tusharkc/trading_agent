"""
Mock Kite client for simulation using historical data from real Kite API.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.domains.trading.kite_client import KiteClient
from app.shared.logger import logger


class MockKiteClient(KiteClient):
    """
    Mock Kite client that extends real KiteClient.
    Uses real historical data but simulates order placement.
    """

    def __init__(self, target_date: datetime):
        """
        Initialize mock client for simulation.

        Args:
            target_date: The date being simulated
        """
        # Initialize parent but allow it to work even without access token for data fetching
        # Ensure target_date is timezone-naive for consistency
        if target_date.tzinfo is not None:
            self.target_date = target_date.replace(tzinfo=None)
        else:
            self.target_date = target_date
        self.simulated_orders = []  # Track simulated orders

        # Try to initialize parent, but don't fail if token missing (for data-only access)
        try:
            super().__init__()
        except Exception as e:
            logger.warning(f"⚠️  Could not initialize Kite client: {e}")
            logger.warning("⚠️  Historical data fetching may require valid access token")
            # Create minimal instance for data fetching
            from app.shared.config import config
            from kiteconnect import KiteConnect

            self.api_key = config.KITE_API_KEY
            self.api_secret = config.KITE_API_SECRET
            self.access_token = config.KITE_ACCESS_TOKEN
            self.kite = KiteConnect(api_key=self.api_key) if self.api_key else None
            if self.kite and self.access_token:
                self.kite.set_access_token(self.access_token)

    def get_historical_data(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str = "5minute",
        continuous: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical 5-minute data for simulation.
        Uses parent class method to get real data from Kite API.
        """
        try:
            if not self.kite:
                raise ValueError("Kite client not initialized")

            data = super().get_historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=continuous,
            )

            # Filter to only include data up to target date (end of day)
            # Kite API returns candles with 'date' key as datetime
            # Ensure target_end is timezone-naive for comparison
            if self.target_date.tzinfo is not None:
                target_end = self.target_date.replace(tzinfo=None).replace(
                    hour=15, minute=30, second=0
                )
            else:
                target_end = self.target_date.replace(hour=15, minute=30, second=0)

            filtered_data = []
            for candle in data:
                candle_date = candle.get("date") or candle.get("timestamp")
                if candle_date is None:
                    continue

                if isinstance(candle_date, str):
                    candle_date = pd.to_datetime(candle_date)
                elif not isinstance(candle_date, datetime):
                    candle_date = pd.to_datetime(candle_date)

                # Ensure candle_date is timezone-naive for comparison
                if hasattr(candle_date, "tz_localize"):
                    if candle_date.tz is not None:
                        candle_date = candle_date.tz_localize(None)
                elif hasattr(candle_date, "tzinfo") and candle_date.tzinfo is not None:
                    # For datetime objects with timezone
                    candle_date = candle_date.replace(tzinfo=None)

                # Convert to datetime if it's a pandas Timestamp
                if hasattr(candle_date, "to_pydatetime"):
                    candle_date = candle_date.to_pydatetime()

                if candle_date <= target_end:
                    filtered_data.append(candle)

            return filtered_data

        except Exception as e:
            logger.error(f"❌ Error fetching historical data: {e}")
            return []

    def get_instrument_token(self, exchange: str, symbol: str) -> Optional[int]:
        """Get instrument token - uses parent method."""
        try:
            return super().get_instrument_token(exchange, symbol)
        except Exception as e:
            logger.error(f"❌ Error getting instrument token for {symbol}: {e}")
            return None

    def place_order(
        self,
        exchange: str,
        tradingsymbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        product: str = "MIS",
        validity: str = "DAY",
        disclosed_quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
        squareoff: Optional[float] = None,
        stoploss: Optional[float] = None,
        trailing_stoploss: Optional[float] = None,
        tag: Optional[str] = None,
    ) -> str:
        """
        Simulate order placement - doesn't place real orders.
        Returns a mock order ID for tracking.
        """
        import uuid

        mock_order_id = f"SIM_{uuid.uuid4().hex[:12]}"

        order_record = {
            "order_id": mock_order_id,
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
            "product": product,
            "status": "COMPLETE",  # Simulated orders are immediately filled
            "timestamp": datetime.utcnow(),
        }

        self.simulated_orders.append(order_record)

        logger.info(
            f"🔵 SIMULATED ORDER: {transaction_type} {quantity} {tradingsymbol} @ {price or 'MARKET'} "
            f"(Order ID: {mock_order_id})"
        )

        return mock_order_id

    def get_quote(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get quotes - in simulation, this would need historical price.
        For now, returns empty dict - simulator should use candle data instead.
        """
        logger.warning(
            "⚠️  get_quote() called in simulation mode - use historical candle data instead"
        )
        return {}

    def cancel_order(self, order_id: str, variety: str = "regular") -> bool:
        """Simulate order cancellation."""
        logger.info(f"🔵 SIMULATED CANCEL: Order {order_id}")
        return True

    def get_simulated_orders(self) -> List[Dict[str, Any]]:
        """Get list of all simulated orders for logging."""
        return self.simulated_orders
