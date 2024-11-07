from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.common import *  # For error codes and other constants
import time
import logging
from datetime import datetime


class StockTrader:
    def __init__(self, ib_connection):
        self.ib = ib_connection
        self.reference_price = 0
        self.buy_count = 0
        self.positions = []
        self.start_time = None
        self.is_trading = False
        self.logger = logging.getLogger('StockTrader')
        self.total_trades = 0
        self.total_profit = 0

    def monitor_and_trade(self, symbol: str, buy_trigger_percentage=-0.01, sell_trigger_percentage=0.01,
                          max_positions=3, position_size=30):
        """
        Monitor real-time prices and execute trades based on conditions
        buy_trigger_percentage: negative percentage indicating price drop to trigger buy
        sell_trigger_percentage: positive percentage indicating price rise to trigger sell
        max_positions: maximum number of positions allowed
        position_size: number of shares per position
        """
        try:
            if not self.ib.is_connected:
                raise ConnectionError("Not connected to IB")

            if not symbol:
                raise ValueError("Symbol cannot be empty")

            # Add more detailed logging
            self.logger.info(f"Starting price monitoring for {symbol}")
            self.logger.info(f"Current connection status: {self.ib.is_connected}")

            # self.ib.start_price_stream(symbol)
            # Add timeout for initial price data
            timeout = 30  # seconds
            start_time = time.time()
            while self.ib.current_price <= 0:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Timeout waiting for initial price data")
                time.sleep(1)


            # Store reference price for calculating triggers
            # reference_price = self.ib.current_price

            STOP_LOSS_PERCENTAGE = -0.02  # 2% stop loss

            while True:
                current_price = self.ib.current_price

                if current_price <= 0:  # Add price validation
                    self.logger.warning("Invalid price received, skipping cycle")
                    time.sleep(1)
                    continue

                price_change = (current_price - self.reference_price) / self.reference_price
                self.logger.info(f"price_change ${price_change:.2f} at reference_price ${self.reference_price:.2f}")
                # Check stop loss for all positions
                for position in self.positions:
                    loss_percentage = (current_price - position['price']) / position['price']
                    if loss_percentage <= STOP_LOSS_PERCENTAGE:
                        self.logger.warning(f"Stop loss triggered at {loss_percentage:.2%}")
                        self.execute_sell_order([position], [], position['shares'], current_price)

                # Check for sell conditions first
                if self.positions:
                    self.check_and_execute_sells(current_price, sell_trigger_percentage)

                # Check for buy conditions
                if len(self.positions) < max_positions and price_change <= buy_trigger_percentage:
                    self.execute_buy_order(current_price, position_size)
                    # Update reference price after buy
                    self.reference_price = current_price

                # Update reference price if price moved significantly
                if abs(price_change) > max(abs(buy_trigger_percentage), sell_trigger_percentage):
                    self.reference_price = current_price
                    self.logger.info(f"Updated reference price to ${self.reference_price:.2f}")

                time.sleep(1)

        except Exception as e:
            self.logger.error(f"Monitoring error: {str(e)}")
            raise

    def check_and_execute_sells(self, current_price, sell_trigger_percentage):
        """Check positions and execute sells based on current price"""
        profitable_positions = []
        positions_to_keep = []
        total_shares_to_sell = 0
        price_at_analysis = current_price

        for position in self.positions:
            profit_percentage = (price_at_analysis - position['price']) / position['price']
            if profit_percentage >= sell_trigger_percentage:
                profitable_positions.append(position)
                total_shares_to_sell += position['shares']
            else:
                positions_to_keep.append(position)

        if profitable_positions:
            self.execute_sell_order(profitable_positions, positions_to_keep,
                                    total_shares_to_sell, price_at_analysis)

    def execute_buy_order(self, current_price, position_size):
        """Execute buy order at current price level"""
        try:
            # Verify connection
            if not self.ib.is_connected:
                self.logger.error("Not connected to IB")
                return False

            # Get next valid order ID
            order_id = self.ib.get_next_order_id()
            if order_id is None:
                self.logger.error("Failed to get valid order ID")
                return False

            # Create contract
            contract = Contract()
            contract.symbol = self.ib.symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"

            # Create limit buy order slightly above current price
            limit_price = current_price * 1.0001  # 0.01% above current price

            order = Order()
            order.action = "BUY"
            order.totalQuantity = position_size
            order.orderType = "LMT"
            order.lmtPrice = limit_price
            # order.tif = "DAY"
            order.tif = 'GTC'  # Good-Til-Canceled
            order.outsideRth = True  # Allow order outside regular trading hours

            # Log order details
            self.logger.info(f"Placing order {order_id}: BUY {position_size} {contract.symbol} @ ${limit_price:.2f}")

            # Place order
            self.ib.placeOrder(order_id, contract, order)

            # Create trade object
            trade = {
                'order': order,
                'contract': contract,
                'order_id': order_id,
                'status': None,
                'filled': 0,
                'avgFillPrice': 0,
                'orderStatus': None
            }

            # Wait for fill
            if self.wait_for_fill(trade):
                actual_fill_price = trade.get('avgFillPrice', current_price)

                # Add position
                self.positions.append({
                    'shares': position_size,
                    'price': actual_fill_price,
                    'timestamp': datetime.now()
                })

                self.logger.info(f"Buy executed: {position_size} shares at ${actual_fill_price:.2f}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Buy execution error: {str(e)}")
            return False

    def execute_sell_order(self, profitable_positions, positions_to_keep,
                           total_shares_to_sell, current_price):
        """Execute sell order for profitable positions"""
        try:
            contract = Contract()
            contract.symbol = self.ib.symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"

            # Create limit sell order slightly below current price
            limit_price = current_price * 0.999  # 0.1% below current price

            order = Order()
            order.action = "SELL"
            order.totalQuantity = total_shares_to_sell
            order.orderType = "LMT"
            order.lmtPrice = limit_price
            order.tif = "DAY"

            trade = self.ib.placeOrder(contract, order)

            if self.wait_for_fill(trade):
                actual_fill_price = trade.orderStatus.avgFillPrice

                # Calculate actual profit
                actual_total_profit = sum(
                    (actual_fill_price - pos['price']) * pos['shares']
                    for pos in profitable_positions
                )

                # Update positions and statistics
                self.positions = positions_to_keep
                self.total_trades += 1
                self.total_profit += actual_total_profit

                self.logger.info(
                    f"Sell executed: {total_shares_to_sell} shares at ${actual_fill_price:.2f}, "
                    f"Profit: ${actual_total_profit:.2f}"
                )
                return True

        except Exception as e:
            self.logger.error(f"Sell execution error: {str(e)}")
            return False

    def wait_for_fill(self, trade, timeout=60):
        """
        Wait for order to fill with timeout
        Returns: True if filled, False if timeout or error
        """
        start_time = time.time()

        while True:
            # Check if timeout reached
            if time.time() - start_time > timeout:
                self.logger.error("Order timeout - cancelling order")
                self.ib.cancelOrder(trade['order_id'])
                return False

            # Get latest order status
            status = self.ib.get_order_status(trade['order_id'])
            if status:
                trade['status'] = status.get('status')
                trade['filled'] = status.get('filled', 0)
                trade['avgFillPrice'] = status.get('avgFillPrice', 0)
                trade['orderStatus'] = status

                # Check if order is complete
                if trade['status'] == 'Filled':
                    return self.handle_order_status(trade)
                elif trade['status'] in ['Cancelled', 'ApiCancelled', 'Error']:
                    return self.handle_order_status(trade)

            time.sleep(1)

    def handle_order_status(self, trade):
        """Handle order status updates"""
        status = trade.get('orderStatus', {})

        if trade['status'] == 'Filled':
            self.logger.info(
                f"Order filled: {trade['filled']} shares at average price ${trade['avgFillPrice']:.2f}"
            )
            return True
        elif trade['status'] in ['Cancelled', 'ApiCancelled']:
            self.logger.warning(f"Order cancelled: {status.get('whyHeld', 'Unknown reason')}")
            return False
        elif trade['status'] == 'Error':
            self.logger.error(f"Order error: {status.get('whyHeld', 'Unknown error')}")
            return False

        return None

    def handle_order_status(self, trade):
        """Handle order status updates"""
        status = trade.orderStatus

        if status.status == 'Filled':
            self.logger.info(
                f"Order filled: {status.filled} shares at average price ${status.avgFillPrice:.2f}"
            )
            return True
        elif status.status in ['Cancelled', 'ApiCancelled']:
            self.logger.warning(f"Order cancelled: {status.whyHeld}")
            return False
        elif status.status == 'Error':
            self.logger.error(f"Order error: {status.whyHeld}")
            return False

        return None

    def get_positions_summary(self):
        """Get summary of current positions"""
        if not self.positions:
            return "No open positions"

        summary = []
        total_value = 0
        total_profit = 0

        for pos in self.positions:
            current_value = pos['shares'] * self.ib.current_price
            position_profit = (self.ib.current_price - pos['price']) * pos['shares']
            profit_percentage = (self.ib.current_price - pos['price']) / pos['price'] * 100

            summary.append({
                'shares': pos['shares'],
                'buy_price': pos['price'],
                'current_price': self.ib.current_price,
                'profit': position_profit,
                'profit_percentage': profit_percentage,
                'value': current_value
            })

            total_value += current_value
            total_profit += position_profit

        return {
            'positions': summary,
            'total_value': total_value,
            'total_profit': total_profit,
            'total_positions': len(self.positions)
        }

    def set_reference_price(self, price):
        self.reference_price = price
        self.logger.info(f"Reference price set to: {price}")

    def start_trading(self):
        if self.reference_price <= 0:
            raise ValueError("Reference price must be set before trading")
        self.is_trading = True
        self.start_time = datetime.now()
        self.logger.info("Trading started")
        self.monitor_and_trade(
            symbol=self.ib.symbol,
            buy_trigger_percentage=-0.01,  # Buy on 1% drop
            sell_trigger_percentage=0.01,  # Sell on 1% gain
            max_positions=3,  # Maximum 3 positions
            position_size=30  # 100 shares per position
        )

    def stop_trading(self):
        self.is_trading = False
        self.start_time = None
        self.logger.info("Trading stopped")
