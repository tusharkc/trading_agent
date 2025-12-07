"""
Signal generator for entry and exit conditions.
"""
from typing import Dict, Optional, Tuple, Any
from app.shared.logger import logger


class SignalGenerator:
    """Signal generator for evaluating entry and exit conditions."""

    def __init__(self):
        """Initialize signal generator."""
        pass

    def check_entry_conditions(self, indicators: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate entry criteria using Ichimoku and MACD indicators.
        Requires at least 2 out of 5 conditions to be met (more is better).
        Args:
            indicators: Dictionary containing all technical indicators
        Returns:
            Tuple of (signal_present, reason)
        """
        try:
            ichimoku = indicators.get("ichimoku", {})
            macd = indicators.get("macd", {})

            conditions_met = []
            conditions_failed = []

            # 1. Price > Ichimoku Cloud (bullish trend)
            price_above_cloud = ichimoku.get("price_above_cloud", False)
            if price_above_cloud:
                conditions_met.append("Price above cloud")
            else:
                conditions_failed.append("Price not above cloud")

            # 2. Tenkan-sen > Kijun-sen (momentum up)
            tenkan_sen = ichimoku.get("tenkan_sen")
            kijun_sen = ichimoku.get("kijun_sen")
            if tenkan_sen and kijun_sen and tenkan_sen > kijun_sen:
                conditions_met.append("Tenkan-sen > Kijun-sen")
            else:
                conditions_failed.append("Tenkan-sen not above Kijun-sen")

            # 3. Cloud color green (Senkou Span A > Senkou Span B)
            cloud_color = ichimoku.get("cloud_color", "")
            if cloud_color == "green":
                conditions_met.append("Cloud color green")
            else:
                conditions_failed.append("Cloud color not green")

            # 4. MACD line > Signal line (bullish momentum)
            macd_above_signal = macd.get("macd_above_signal", False)
            if macd_above_signal:
                conditions_met.append("MACD > Signal")
            else:
                conditions_failed.append("MACD not above signal")

            # 5. MACD histogram > 0 and rising
            histogram = macd.get("histogram")
            histogram_rising = macd.get("histogram_rising", False)
            if histogram and histogram > 0 and histogram_rising:
                conditions_met.append("MACD histogram rising")
            else:
                conditions_failed.append("MACD histogram not rising")

            # Check if at least 2 conditions are met
            num_conditions_met = len(conditions_met)
            min_required = 2

            if num_conditions_met >= min_required:
                # More conditions = stronger signal
                strength = "Strong" if num_conditions_met >= 4 else "Moderate" if num_conditions_met >= 3 else "Weak"
                reason = f"{strength} signal: {num_conditions_met}/5 conditions met ({', '.join(conditions_met)})"
                return True, reason
            else:
                failed_reason = f"Insufficient signals: {num_conditions_met}/5 met. Met: {', '.join(conditions_met) if conditions_met else 'None'}. Failed: {', '.join(conditions_failed[:3])}"
                return False, failed_reason

        except Exception as e:
            logger.error(f"❌ Error checking entry conditions: {e}")
            return False, f"Error: {str(e)}"

    def check_exit_conditions(
        self, indicators: Dict[str, Any], position_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate exit triggers with flexible logic.
        - Stop loss and take profit always respected
        - Technical exits only trigger when position is losing money
        - This allows profitable positions to run toward take-profit
        Args:
            indicators: Dictionary containing all technical indicators
            position_data: Dictionary with position info (stop_loss, take_profit, entry_price)
        Returns:
            Tuple of (exit_triggered, exit_reason)
        """
        try:
            ichimoku = indicators.get("ichimoku", {})
            macd = indicators.get("macd", {})
            current_price = ichimoku.get("current_price")

            if not current_price:
                return False, None

            stop_loss = position_data.get("stop_loss")
            take_profit = position_data.get("take_profit")
            entry_price = position_data.get("entry_price")

            # Calculate current P&L percentage
            pnl_percent = ((current_price - entry_price) / entry_price) * 100.0

            # 1. Always respect take-profit (highest priority)
            if take_profit and current_price >= take_profit:
                return True, "TAKE_PROFIT"

            # 2. Always respect stop-loss (highest priority)
            if stop_loss and current_price <= stop_loss:
                return True, "STOP_LOSS"

            # 3. Technical exits ONLY if position is losing money
            # This prevents cutting winners short and lets profits run
            if pnl_percent < 0:
                # MACD reversal: MACD below signal with negative histogram
                macd_above_signal = macd.get("macd_above_signal", False)
                histogram = macd.get("histogram")
                
                if not macd_above_signal and histogram and histogram < 0:
                    # Check if histogram is meaningfully negative (not just noise)
                    # Use a threshold relative to entry price to avoid false signals
                    histogram_threshold = -(abs(entry_price) * 0.001)  # 0.1% of entry price
                    if histogram < histogram_threshold:
                        return True, "MACD_REVERSAL"
                
                # Price below cloud - strong reversal signal
                # Only exit if position is losing more than 0.5% to avoid premature exits on noise
                price_below_cloud = ichimoku.get("price_below_cloud", False)
                min_loss_threshold = -0.5  # Only exit if losing more than 0.5%
                if price_below_cloud and pnl_percent <= min_loss_threshold:
                    return True, "PRICE_BELOW_CLOUD"

            # If position is profitable (pnl_percent >= 0), don't exit on technical signals
            # Let it run to take-profit or stop-loss only

            return False, None

        except Exception as e:
            logger.error(f"❌ Error checking exit conditions: {e}")
            return False, None

    def generate_entry_signal(self, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate entry signal if all conditions are met.
        Args:
            indicators: Dictionary containing all technical indicators
        Returns:
            Signal dictionary or None
        """
        try:
            signal_present, reason = self.check_entry_conditions(indicators)

            if signal_present:
                return {
                    "signal": "ENTRY",
                    "reason": reason,
                    "timestamp": indicators.get("ichimoku", {}).get("current_price"),
                }
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error generating entry signal: {e}")
            return None

    def generate_exit_signal(
        self, indicators: Dict[str, Any], position_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate exit signal if any exit condition is met.
        Args:
            indicators: Dictionary containing all technical indicators
            position_data: Dictionary with position info
        Returns:
            Signal dictionary or None
        """
        try:
            exit_triggered, exit_reason = self.check_exit_conditions(indicators, position_data)

            if exit_triggered:
                return {
                    "signal": "EXIT",
                    "reason": exit_reason,
                    "price": indicators.get("ichimoku", {}).get("current_price"),
                }
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error generating exit signal: {e}")
            return None

