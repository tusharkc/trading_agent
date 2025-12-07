"""
Kite API client wrapper for order placement and data fetching.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from kiteconnect import KiteConnect, KiteTicker
from app.shared.config import config
from app.shared.logger import logger


class KiteClient:
    """Kite API client wrapper with authentication and order management."""

    def __init__(self):
        """Initialize Kite client with API credentials."""
        if not config.KITE_API_KEY:
            raise ValueError("KITE_API_KEY is required")
        if not config.KITE_API_SECRET:
            raise ValueError("KITE_API_SECRET is required")

        self.api_key = config.KITE_API_KEY
        self.api_secret = config.KITE_API_SECRET
        self.access_token = config.KITE_ACCESS_TOKEN

        self.kite = None
        self._initialize_kite()

    def _initialize_kite(self):
        """Initialize KiteConnect instance."""
        self.kite = KiteConnect(api_key=self.api_key)
        if self.access_token:
            self.kite.set_access_token(self.access_token)

    def authenticate(self) -> str:
        """
        Handle login flow and generate access token.
        Returns login URL for manual authentication.
        """
        try:
            login_url = self.kite.login_url()
            logger.info(f"🔐 Please visit this URL to login: {login_url}")
            logger.info("After login, copy the 'request_token' from the redirected URL")
            return login_url
        except Exception as e:
            logger.error(f"❌ Error generating login URL: {e}")
            raise

    def generate_session(self, request_token: str) -> str:
        """
        Generate access token from request token.
        Returns access token.
        """
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = data["access_token"]
            self.kite.set_access_token(access_token)
            self.access_token = access_token
            logger.info("✅ Successfully generated and set access token")
            return access_token
        except Exception as e:
            logger.error(f"❌ Error generating session: {e}")
            raise

    def refresh_token(self) -> bool:
        """
        Refresh access token (Kite tokens expire daily).
        Returns True if successful.
        """
        # Note: Kite tokens don't auto-refresh, they need to be regenerated daily
        # This method can be used to validate token is still valid
        try:
            profile = self.kite.profile()
            logger.info(f"✅ Token is valid. User: {profile.get('user_name')}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Token validation failed: {e}")
            logger.warning(
                "Please regenerate access token using authenticate() and generate_session()"
            )
            return False

    def get_quote(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch real-time quotes for given symbols.
        Symbols should be in Kite format: 'NSE:RELIANCE'
        """
        try:
            quotes = self.kite.quote(symbols)
            return quotes
        except Exception as e:
            logger.error(f"❌ Error fetching quotes: {e}")
            raise

    def get_historical_data(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str = "5minute",
        continuous: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical OHLCV data for indicators.
        interval: 'minute', '3minute', '5minute', '15minute', '30minute', '60minute', 'day'
        Returns list of candle dictionaries.
        """
        try:
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=continuous,
            )
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching historical data: {e}")
            raise

    def get_instrument_token(self, exchange: str, symbol: str) -> Optional[int]:
        """
        Get instrument token for a symbol.
        Returns instrument token or None if not found.
        """
        try:
            instruments = self.kite.instruments(exchange=exchange)
            for instrument in instruments:
                if instrument["tradingsymbol"] == symbol:
                    return instrument["instrument_token"]
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching instrument token: {e}")
            return None

    def get_instruments_list(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        """Get all instruments for an exchange."""
        try:
            instruments = self.kite.instruments(exchange=exchange)
            return instruments
        except Exception as e:
            logger.error(f"❌ Error fetching instruments list: {e}")
            raise

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
        Place an order.
        Returns order ID.
        """
        try:
            order_params = {
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "transaction_type": transaction_type,  # BUY or SELL
                "quantity": quantity,
                "order_type": order_type,  # MARKET, LIMIT, SL, SL-M
                "product": product,  # MIS, CNC, NRML
                "validity": validity,  # DAY, IOC
            }

            if price is not None:
                order_params["price"] = price
            if disclosed_quantity is not None:
                order_params["disclosed_quantity"] = disclosed_quantity
            if trigger_price is not None:
                order_params["trigger_price"] = trigger_price
            if squareoff is not None:
                order_params["squareoff"] = squareoff
            if stoploss is not None:
                order_params["stoploss"] = stoploss
            if trailing_stoploss is not None:
                order_params["trailing_stoploss"] = trailing_stoploss
            if tag is not None:
                order_params["tag"] = tag

            order_id = self.kite.place_order(**order_params)
            logger.info(
                f"✅ Order placed: {order_id} for {tradingsymbol} {transaction_type} {quantity}"
            )
            return order_id
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            raise

    def get_positions(self) -> Dict[str, Any]:
        """Fetch current positions from Kite."""
        try:
            positions = self.kite.positions()
            return positions
        except Exception as e:
            logger.error(f"❌ Error fetching positions: {e}")
            raise

    def get_orders(self) -> List[Dict[str, Any]]:
        """Fetch all orders."""
        try:
            orders = self.kite.orders()
            return orders
        except Exception as e:
            logger.error(f"❌ Error fetching orders: {e}")
            raise

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific order."""
        try:
            orders = self.kite.orders()
            for order in orders:
                if order["order_id"] == order_id:
                    return order
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching order status: {e}")
            return None

    def cancel_order(self, order_id: str, variety: str = "regular") -> bool:
        """Cancel a pending order."""
        try:
            self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info(f"✅ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        validity: Optional[str] = None,
        variety: str = "regular",
    ) -> bool:
        """Modify an existing order."""
        try:
            modify_params = {}
            if quantity is not None:
                modify_params["quantity"] = quantity
            if price is not None:
                modify_params["price"] = price
            if order_type is not None:
                modify_params["order_type"] = order_type
            if validity is not None:
                modify_params["validity"] = validity

            self.kite.modify_order(variety=variety, order_id=order_id, **modify_params)
            logger.info(f"✅ Order modified: {order_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error modifying order {order_id}: {e}")
            return False

    def get_margins(self) -> Dict[str, Any]:
        """Get account margins."""
        try:
            margins = self.kite.margins()
            return margins
        except Exception as e:
            logger.error(f"❌ Error fetching margins: {e}")
            raise

    def get_available_capital(self) -> float:
        """
        Get available trading capital from account.
        Returns available cash from equity margin.
        Raises ValueError if capital cannot be fetched.
        """
        try:
            margins = self.get_margins()
            
            # Kite API returns margins with equity and commodity sections
            equity = margins.get("equity", {})
            if not equity:
                raise ValueError("No equity margin data found in account")
            
            available = equity.get("available", {})
            if not available:
                raise ValueError("No available margin data found in account")
            
            # Try to get available cash first
            available_cash = available.get("cash")
            if available_cash is not None:
                capital = float(available_cash)
                if capital <= 0:
                    raise ValueError(f"Available capital is zero or negative: ₹{capital}")
                return capital
            
            # Fallback to net equity if cash not available
            net = equity.get("net")
            if net is not None:
                capital = float(net)
                if capital <= 0:
                    raise ValueError(f"Net equity is zero or negative: ₹{capital}")
                logger.warning("⚠️  Using net equity instead of available cash")
                return capital
            
            raise ValueError("Could not extract available capital from margins response")
            
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            raise ValueError(f"Error fetching available capital: {e}") from e

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get long-term holdings."""
        try:
            holdings = self.kite.holdings()
            return holdings
        except Exception as e:
            logger.error(f"❌ Error fetching holdings: {e}")
            raise

    @staticmethod
    def convert_symbol_to_kite_format(symbol: str, exchange: str = "NSE") -> str:
        """Convert symbol like 'RELIANCE' to Kite format 'NSE:RELIANCE'."""
        return f"{exchange}:{symbol}"

    @staticmethod
    def convert_kite_format_to_symbol(kite_symbol: str) -> str:
        """Convert Kite format 'NSE:RELIANCE' to symbol 'RELIANCE'."""
        if ":" in kite_symbol:
            return kite_symbol.split(":")[1]
        return kite_symbol
