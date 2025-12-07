"""
Technical analyzer for calculating indicators manually using pandas/numpy.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
from app.shared.logger import logger


class TechnicalAnalyzer:
    """Technical analyzer for calculating Ichimoku Cloud, MACD, and volume indicators."""

    def __init__(self):
        """Initialize technical analyzer."""
        pass

    def calculate_ichimoku(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Ichimoku Cloud components manually.
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        Returns:
            Dictionary with Ichimoku components and cloud information
        """
        try:
            if len(df) < 52:  # Need at least 52 periods for full Ichimoku
                logger.warning(f"⚠️  Insufficient data for Ichimoku: {len(df)} periods (need 52)")
                return {}

            high = df["high"]
            low = df["low"]
            close = df["close"]

            # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
            tenkan_high = high.rolling(window=9).max()
            tenkan_low = low.rolling(window=9).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2

            # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
            kijun_high = high.rolling(window=26).max()
            kijun_low = low.rolling(window=26).min()
            kijun_sen = (kijun_high + kijun_low) / 2

            # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted 26 periods ahead
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

            # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods ahead
            senkou_high = high.rolling(window=52).max()
            senkou_low = low.rolling(window=52).min()
            senkou_span_b = ((senkou_high + senkou_low) / 2).shift(26)

            # Chikou Span (Lagging Span): Close price shifted 26 periods back
            chikou_span = close.shift(-26)

            # Get latest values
            tenkan_sen_val = tenkan_sen.iloc[-1]
            kijun_sen_val = kijun_sen.iloc[-1]
            senkou_span_a_val = senkou_span_a.iloc[-1]
            senkou_span_b_val = senkou_span_b.iloc[-1]
            chikou_span_val = chikou_span.iloc[-1]

            # Get current price
            current_price = close.iloc[-1]

            # Determine cloud position (use current cloud - not shifted)
            # For current cloud, we need to look at the cloud that applies to current price
            current_senkou_a = senkou_span_a.iloc[-1] if not pd.isna(senkou_span_a.iloc[-1]) else None
            current_senkou_b = senkou_span_b.iloc[-1] if not pd.isna(senkou_span_b.iloc[-1]) else None

            # If shifted values are NaN, use the last available cloud values
            if pd.isna(current_senkou_a) or pd.isna(current_senkou_b):
                # Look back for the last valid cloud values (they're shifted forward)
                for i in range(len(senkou_span_a) - 1, -1, -1):
                    if not pd.isna(senkou_span_a.iloc[i]) and not pd.isna(senkou_span_b.iloc[i]):
                        current_senkou_a = senkou_span_a.iloc[i]
                        current_senkou_b = senkou_span_b.iloc[i]
                        break

            cloud_top = max(current_senkou_a, current_senkou_b) if (current_senkou_a and current_senkou_b and not pd.isna(current_senkou_a) and not pd.isna(current_senkou_b)) else None
            cloud_bottom = min(current_senkou_a, current_senkou_b) if (current_senkou_a and current_senkou_b and not pd.isna(current_senkou_a) and not pd.isna(current_senkou_b)) else None

            price_above_cloud = current_price > cloud_top if cloud_top else False
            price_below_cloud = current_price < cloud_bottom if cloud_bottom else False

            # Determine cloud color (green/bullish if Span A > Span B)
            cloud_color = "green" if (current_senkou_a and current_senkou_b and not pd.isna(current_senkou_a) and not pd.isna(current_senkou_b) and current_senkou_a > current_senkou_b) else "red"

            return {
                "tenkan_sen": float(tenkan_sen_val) if not pd.isna(tenkan_sen_val) else None,
                "kijun_sen": float(kijun_sen_val) if not pd.isna(kijun_sen_val) else None,
                "senkou_span_a": float(current_senkou_a) if current_senkou_a and not pd.isna(current_senkou_a) else None,
                "senkou_span_b": float(current_senkou_b) if current_senkou_b and not pd.isna(current_senkou_b) else None,
                "chikou_span": float(chikou_span_val) if not pd.isna(chikou_span_val) else None,
                "cloud_top": float(cloud_top) if cloud_top else None,
                "cloud_bottom": float(cloud_bottom) if cloud_bottom else None,
                "price_above_cloud": price_above_cloud,
                "price_below_cloud": price_below_cloud,
                "cloud_color": cloud_color,
                "current_price": float(current_price),
            }

        except Exception as e:
            logger.error(f"❌ Error calculating Ichimoku: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
        """
        Calculate MACD indicator manually.
        Args:
            df: DataFrame with close price
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)
        Returns:
            Dictionary with MACD line, signal line, and histogram
        """
        try:
            if len(df) < slow + signal:
                logger.warning(f"⚠️  Insufficient data for MACD: {len(df)} periods")
                return {}

            close = df["close"]

            # Calculate EMAs
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()

            # MACD line = Fast EMA - Slow EMA
            macd_line = ema_fast - ema_slow

            # Signal line = 9-period EMA of MACD line
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()

            # Histogram = MACD line - Signal line
            histogram = macd_line - signal_line

            # Get latest values
            macd_val = macd_line.iloc[-1]
            signal_val = signal_line.iloc[-1]
            hist_val = histogram.iloc[-1]

            # Determine if histogram is rising
            histogram_rising = False
            if len(histogram) > 1:
                prev_hist = histogram.iloc[-2]
                if not pd.isna(hist_val) and not pd.isna(prev_hist):
                    histogram_rising = hist_val > prev_hist

            return {
                "macd_line": float(macd_val) if not pd.isna(macd_val) else None,
                "signal_line": float(signal_val) if not pd.isna(signal_val) else None,
                "histogram": float(hist_val) if not pd.isna(hist_val) else None,
                "histogram_rising": histogram_rising,
                "macd_above_signal": macd_val > signal_val if (not pd.isna(macd_val) and not pd.isna(signal_val)) else False,
            }

        except Exception as e:
            logger.error(f"❌ Error calculating MACD: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def calculate_volume_indicator(self, df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
        """
        Calculate volume indicators.
        Args:
            df: DataFrame with volume column
            period: Period for moving average (default: 20)
        Returns:
            Dictionary with volume average and comparison
        """
        try:
            if len(df) < period:
                logger.warning(f"⚠️  Insufficient data for volume indicator: {len(df)} periods (need {period})")
                return {}

            if "volume" not in df.columns:
                logger.warning("⚠️  Volume column not found in DataFrame")
                return {}

            # Calculate volume moving average
            volume_ma = df["volume"].rolling(window=period).mean()

            # Get latest values
            current_volume = df["volume"].iloc[-1]
            volume_avg = volume_ma.iloc[-1]

            return {
                "current_volume": float(current_volume) if not pd.isna(current_volume) else None,
                "volume_average": float(volume_avg) if not pd.isna(volume_avg) else None,
                "volume_above_average": current_volume > volume_avg if (not pd.isna(current_volume) and not pd.isna(volume_avg)) else False,
            }

        except Exception as e:
            logger.error(f"❌ Error calculating volume indicator: {e}")
            return {}

    def get_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate all indicators for a stock.
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        Returns:
            Dictionary containing all indicators
        """
        try:
            # Ensure DataFrame has required columns
            required_columns = ["open", "high", "low", "close"]
            if not all(col in df.columns for col in required_columns):
                logger.error(f"❌ DataFrame missing required columns. Expected: {required_columns}")
                return {}

            # Ensure DataFrame is sorted by date/index
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()

            indicators = {}

            # Calculate Ichimoku Cloud
            ichimoku = self.calculate_ichimoku(df)
            indicators["ichimoku"] = ichimoku

            # Calculate MACD
            macd = self.calculate_macd(df)
            indicators["macd"] = macd

            # Calculate Volume Indicator
            volume_ind = self.calculate_volume_indicator(df)
            indicators["volume"] = volume_ind

            return indicators

        except Exception as e:
            logger.error(f"❌ Error getting indicators: {e}")
            return {}

    def prepare_dataframe_from_candles(self, candles: list) -> Optional[pd.DataFrame]:
        """
        Convert list of candle dictionaries to pandas DataFrame.
        Args:
            candles: List of candle dicts with keys: timestamp, open, high, low, close, volume
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if not candles:
                return None

            df = pd.DataFrame(candles)

            # Convert timestamp to datetime if it's a string
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df.set_index("timestamp", inplace=True)
            elif df.index.dtype == "object":
                df.index = pd.to_datetime(df.index)

            # Ensure required columns exist
            required = ["open", "high", "low", "close"]
            if not all(col in df.columns for col in required):
                logger.error(f"❌ Missing required columns in candles: {required}")
                return None

            # Ensure volume column exists (create empty if not)
            if "volume" not in df.columns:
                df["volume"] = 0

            # Sort by index
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error(f"❌ Error preparing DataFrame from candles: {e}")
            return None
