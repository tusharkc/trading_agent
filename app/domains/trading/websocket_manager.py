"""
WebSocket manager for real-time tick data and candle aggregation.
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Any
from collections import defaultdict
from kiteconnect import KiteTicker
from app.shared.config import config
from app.shared.logger import logger


class WebSocketManager:
    """WebSocket manager for real-time tick data and 5-minute candle aggregation."""

    def __init__(self, kite_client):
        """
        Initialize WebSocket manager.
        Args:
            kite_client: KiteClient instance with access token
        """
        self.kite_client = kite_client
        self.kws = None
        self.is_connected = False
        self.subscribed_instruments = set()
        
        # Tick storage for candle aggregation
        self.ticks_buffer = defaultdict(list)  # {instrument_token: [ticks]}
        
        # Candle storage (5-minute candles)
        self.candles = defaultdict(list)  # {instrument_token: [candles]}
        
        # Callbacks
        self.on_candle_close_callback: Optional[Callable] = None
        
        # Lock for thread-safe operations
        self.lock = threading.Lock()
        
        # Candle aggregation timing
        self.candle_interval = 5 * 60  # 5 minutes in seconds
        self.last_candle_time = {}

    def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            if not self.kite_client.access_token:
                logger.error("❌ Access token not available for WebSocket connection")
                return False

            self.kws = KiteTicker(
                api_key=self.kite_client.api_key,
                access_token=self.kite_client.access_token,
            )

            # Set callbacks
            self.kws.on_ticks = self._on_ticks
            self.kws.on_connect = self._on_connect
            self.kws.on_close = self._on_close
            self.kws.on_error = self._on_error
            self.kws.on_reconnect = self._on_reconnect
            self.kws.on_noreconnect = self._on_noreconnect

            # Start connection
            self.kws.connect(threaded=True)
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self.is_connected:
                logger.info("✅ WebSocket connected successfully")
                return True
            else:
                logger.error("❌ WebSocket connection timeout")
                return False

        except Exception as e:
            logger.error(f"❌ Error connecting WebSocket: {e}")
            return False

    def subscribe(self, instrument_tokens: List[int], mode: int = KiteTicker.MODE_FULL):
        """
        Subscribe to instrument tokens for tick data.
        Args:
            instrument_tokens: List of instrument tokens to subscribe
            mode: MODE_LTP, MODE_QUOTE, or MODE_FULL
        """
        try:
            if not self.is_connected:
                logger.error("❌ WebSocket not connected. Call connect() first.")
                return

            instrument_tokens_list = list(instrument_tokens)
            self.kws.subscribe(instrument_tokens_list)
            self.kws.set_mode(mode, instrument_tokens_list)
            
            # Track subscribed instruments
            self.subscribed_instruments.update(instrument_tokens_list)
            
            logger.info(f"✅ Subscribed to {len(instrument_tokens_list)} instruments")

        except Exception as e:
            logger.error(f"❌ Error subscribing to instruments: {e}")

    def unsubscribe(self, instrument_tokens: List[int]):
        """Unsubscribe from instrument tokens."""
        try:
            if not self.is_connected:
                return

            instrument_tokens_list = list(instrument_tokens)
            self.kws.unsubscribe(instrument_tokens_list)
            self.subscribed_instruments.difference_update(instrument_tokens_list)
            logger.info(f"✅ Unsubscribed from {len(instrument_tokens_list)} instruments")

        except Exception as e:
            logger.error(f"❌ Error unsubscribing from instruments: {e}")

    def set_candle_close_callback(self, callback: Callable):
        """Set callback function to be called when a 5-minute candle closes."""
        self.on_candle_close_callback = callback

    def _on_ticks(self, ws, ticks):
        """Handle incoming tick data."""
        try:
            for tick in ticks:
                instrument_token = tick["instrument_token"]
                
                # Add tick to buffer
                with self.lock:
                    self.ticks_buffer[instrument_token].append({
                        "timestamp": datetime.now(),
                        "last_price": tick.get("last_price"),
                        "volume": tick.get("volume", 0),
                        "ohlc": tick.get("ohlc", {}),
                    })
                
                # Check if we need to aggregate to candle
                self._check_and_aggregate_candle(instrument_token)

        except Exception as e:
            logger.error(f"❌ Error processing ticks: {e}")

    def _check_and_aggregate_candle(self, instrument_token: int):
        """Check if enough time has passed and aggregate ticks into candle."""
        current_time = datetime.now()
        current_minute = current_time.replace(second=0, microsecond=0)
        
        # Round down to nearest 5-minute interval
        minutes = current_minute.minute
        rounded_minutes = (minutes // 5) * 5
        candle_start = current_minute.replace(minute=rounded_minutes)
        
        # Check if we need to create a new candle
        last_candle_time = self.last_candle_time.get(instrument_token)
        
        if last_candle_time is None or candle_start > last_candle_time:
            # Close previous candle if exists
            if last_candle_time is not None:
                self._close_candle(instrument_token)
            
            # Start new candle
            self.last_candle_time[instrument_token] = candle_start

    def _close_candle(self, instrument_token: int):
        """Aggregate ticks into a completed 5-minute candle."""
        try:
            with self.lock:
                ticks = self.ticks_buffer.get(instrument_token, [])
                
                if not ticks:
                    return
                
                # Aggregate ticks into OHLCV candle
                prices = [tick["last_price"] for tick in ticks if tick.get("last_price")]
                volumes = [tick["volume"] for tick in ticks if tick.get("volume")]
                
                if not prices:
                    # Clear buffer and return
                    self.ticks_buffer[instrument_token] = []
                    return
                
                candle = {
                    "instrument_token": instrument_token,
                    "timestamp": self.last_candle_time[instrument_token],
                    "open": prices[0],
                    "high": max(prices),
                    "low": min(prices),
                    "close": prices[-1],
                    "volume": sum(volumes),
                }
                
                # Store candle
                self.candles[instrument_token].append(candle)
                
                # Keep only last 100 candles to avoid memory issues
                if len(self.candles[instrument_token]) > 100:
                    self.candles[instrument_token] = self.candles[instrument_token][-100:]
                
                # Clear tick buffer
                self.ticks_buffer[instrument_token] = []
                
                logger.info(
                    f"📊 Candle closed for {instrument_token}: "
                    f"O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}"
                )
                
                # Call callback if set
                if self.on_candle_close_callback:
                    self.on_candle_close_callback(instrument_token, candle)

        except Exception as e:
            logger.error(f"❌ Error closing candle: {e}")

    def get_latest_candle(self, instrument_token: int) -> Optional[Dict[str, Any]]:
        """Get the latest completed candle for an instrument."""
        with self.lock:
            candles = self.candles.get(instrument_token, [])
            return candles[-1] if candles else None

    def get_candles(self, instrument_token: int, count: int = 20) -> List[Dict[str, Any]]:
        """Get last N candles for an instrument."""
        with self.lock:
            candles = self.candles.get(instrument_token, [])
            return candles[-count:] if candles else []

    def _on_connect(self, ws, response):
        """Handle WebSocket connection."""
        self.is_connected = True
        logger.info("✅ WebSocket connected")

    def _on_close(self, ws, code, reason):
        """Handle WebSocket close."""
        self.is_connected = False
        logger.warning(f"⚠️  WebSocket closed: {code} - {reason}")

    def _on_error(self, ws, code, reason):
        """Handle WebSocket error."""
        logger.error(f"❌ WebSocket error: {code} - {reason}")

    def _on_reconnect(self, ws, attempts_count):
        """Handle WebSocket reconnection."""
        logger.info(f"🔄 WebSocket reconnecting (attempt {attempts_count})")
        # Resubscribe to instruments
        if self.subscribed_instruments:
            self.subscribe(list(self.subscribed_instruments))

    def _on_noreconnect(self, ws):
        """Handle WebSocket reconnection failure."""
        logger.error("❌ WebSocket reconnection failed")
        self.is_connected = False

    def disconnect(self):
        """Disconnect WebSocket connection."""
        try:
            if self.kws:
                # Close all candles before disconnecting
                for instrument_token in list(self.ticks_buffer.keys()):
                    if self.last_candle_time.get(instrument_token):
                        self._close_candle(instrument_token)
                
                self.kws.close()
                self.is_connected = False
                logger.info("✅ WebSocket disconnected")
        except Exception as e:
            logger.error(f"❌ Error disconnecting WebSocket: {e}")

