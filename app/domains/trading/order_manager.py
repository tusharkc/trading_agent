"""
Order manager for placing and tracking orders.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.domains.trading.models.order import Order, OrderType, TransactionType, OrderStatus
from app.domains.trading.models.db import get_session
from app.domains.trading.kite_client import KiteClient
from app.shared.logger import logger


class OrderManager:
    """Order manager for executing and tracking orders."""

    def __init__(self, kite_client: KiteClient):
        """
        Initialize order manager.
        Args:
            kite_client: KiteClient instance
        """
        self.kite_client = kite_client
        self.session = get_session()

    def place_market_order(
        self, exchange: str, symbol: str, transaction_type: str, quantity: int
    ) -> Optional[str]:
        """Place a market buy/sell order."""
        try:
            order_id = self.kite_client.place_order(
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type="MARKET",
            )
            return order_id
        except Exception as e:
            logger.error(f"❌ Error placing market order: {e}")
            return None

    def place_stop_loss_order(
        self, exchange: str, symbol: str, quantity: int, trigger_price: float
    ) -> Optional[str]:
        """Place a stop-loss order (SL-M)."""
        try:
            # Round trigger price to tick size
            tick_size = self.kite_client.get_tick_size(exchange, symbol)
            rounded_trigger = self.kite_client.round_to_tick_size(trigger_price, tick_size)
            
            order_id = self.kite_client.place_order(
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type="SELL",
                quantity=quantity,
                order_type="SL-M",
                trigger_price=rounded_trigger,
            )
            return order_id
        except Exception as e:
            logger.error(f"❌ Error placing stop-loss order: {e}")
            return None

    def place_take_profit_order(
        self, exchange: str, symbol: str, quantity: int, price: float
    ) -> Optional[str]:
        """Place a limit order for take-profit."""
        try:
            # Round price to tick size
            tick_size = self.kite_client.get_tick_size(exchange, symbol)
            rounded_price = self.kite_client.round_to_tick_size(price, tick_size)
            
            order_id = self.kite_client.place_order(
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type="SELL",
                quantity=quantity,
                order_type="LIMIT",
                price=rounded_price,
            )
            return order_id
        except Exception as e:
            logger.error(f"❌ Error placing take-profit order: {e}")
            return None

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an order from Kite."""
        try:
            return self.kite_client.get_order_status(order_id)
        except Exception as e:
            logger.error(f"❌ Error getting order status: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        try:
            return self.kite_client.cancel_order(order_id)
        except Exception as e:
            logger.error(f"❌ Error cancelling order: {e}")
            return False

    def execute_entry(
        self, exchange: str, symbol: str, quantity: int, stop_loss: float, take_profit: float
    ) -> Dict[str, Optional[str]]:
        """
        Execute complete entry flow: buy order + stop-loss + take-profit.
        Returns dict with order IDs.
        """
        try:
            # Place market buy order
            buy_order_id = self.place_market_order(exchange, symbol, "BUY", quantity)
            if not buy_order_id:
                return {"buy_order": None, "stop_loss_order": None, "take_profit_order": None}

            # Wait a bit for buy order to execute (in production, poll for status)
            import time
            time.sleep(2)

            # Place stop-loss order
            sl_order_id = None
            if stop_loss:
                sl_order_id = self.place_stop_loss_order(exchange, symbol, quantity, stop_loss)

            # Place take-profit order
            tp_order_id = None
            if take_profit:
                tp_order_id = self.place_take_profit_order(exchange, symbol, quantity, take_profit)

            logger.info(
                f"✅ Entry executed: {symbol} - Buy: {buy_order_id}, SL: {sl_order_id}, TP: {tp_order_id}"
            )

            return {
                "buy_order": buy_order_id,
                "stop_loss_order": sl_order_id,
                "take_profit_order": tp_order_id,
            }

        except Exception as e:
            logger.error(f"❌ Error executing entry: {e}")
            return {"buy_order": None, "stop_loss_order": None, "take_profit_order": None}

    def execute_exit(self, exchange: str, symbol: str, quantity: int, order_ids: List[str]) -> Optional[str]:
        """
        Execute exit flow: market sell + cancel SL/TP orders.
        Returns sell order ID.
        """
        try:
            # Cancel pending orders (SL and TP)
            for order_id in order_ids:
                if order_id:
                    self.cancel_order(order_id)

            # Place market sell order
            sell_order_id = self.place_market_order(exchange, symbol, "SELL", quantity)
            logger.info(f"✅ Exit executed: {symbol} - Sell: {sell_order_id}")
            return sell_order_id

        except Exception as e:
            logger.error(f"❌ Error executing exit: {e}")
            return None

    def create_order_record(
        self,
        stock_symbol: str,
        order_type: OrderType,
        transaction_type: TransactionType,
        quantity: int,
        price: Optional[float] = None,
        kite_order_id: Optional[str] = None,
    ) -> Order:
        """Create order record in database."""
        try:
            order = Order(
                stock_symbol=stock_symbol,
                order_type=order_type,
                transaction_type=transaction_type,
                quantity=quantity,
                price=price,
                kite_order_id=kite_order_id,
                status=OrderStatus.PENDING,
                timestamp=datetime.utcnow(),
            )
            self.session.add(order)
            self.session.commit()
            return order
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error creating order record: {e}")
            raise

    def update_order_status(self, order_id: int, status: OrderStatus, **kwargs) -> bool:
        """Update order status in database."""
        try:
            order = self.session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False

            order.status = status
            for key, value in kwargs.items():
                if hasattr(order, key):
                    setattr(order, key, value)

            order.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error updating order status: {e}")
            return False

