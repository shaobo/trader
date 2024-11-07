from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
import queue
import logging

class IBConnection(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
        self.orders = {}
        self.order_id_ready = threading.Event()
        self.logger = logging.getLogger('IBConnection')
        self.current_price = 0
        self.symbol = None
        self.is_connected = False
        self.data = {}
        self.contract = None
        self.gui = None

    def connect_and_init(self, host='127.0.0.1', port=7497, client_id=1):
        """Connect to TWS and initialize order ID"""
        try:
            # Connect to TWS
            self.connect(host, port, client_id)
            # Start the client thread
            thread = threading.Thread(target=self.run)
            thread.daemon = True
            thread.start()

            # Wait for nextValidId to be received
            self.logger.info("Waiting for valid order ID...")
            timeout = 30  # seconds
            if not self.order_id_ready.wait(timeout):
                raise TimeoutError("Timeout waiting for valid order ID")

            self.is_connected = True
            self.logger.info(f"Connected and initialized. Next order ID: {self.next_order_id}")
            return True

        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            self.is_connected = False
            return False

    def nextValidId(self, orderId: int):
        """Called by TWS with next valid order ID"""
        self.next_order_id = orderId
        self.logger.info(f"Received next valid order ID: {orderId}")

    def get_next_order_id(self):
        """Get and increment next valid order ID"""
        if self.next_order_id is None:
            self.logger.error("No valid order ID available")
            return None

        current_id = self.next_order_id
        self.next_order_id += 1
        return current_id

    def orderStatus(self, orderId, status, filled, remaining,
                   avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """Store order status updates"""
        self.orders[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'whyHeld': whyHeld
        }
        self.logger.info(f"Order {orderId} status: {status}, Filled: {filled} @ {avgFillPrice}")

    def get_order_status(self, order_id):
        """Get current status for an order"""
        return self.orders.get(order_id)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Handle error messages from TWS"""
        self.logger.error(f"Error {errorCode}: {errorString}")

    def start_price_stream(self, symbol):
        if not self.is_connected:
            self.logger.error("Not connected to IB")
            return
        self.symbol = symbol
        self.contract = self.create_contract(symbol)

        # Add debug logging
        self.logger.info(f"Requesting market data for {symbol}")
        # Request all tick types
        # generic_tick_list = "233"  # Request all price data
        generic_tick_list = ""  # Request all price data
        self.reqMktData(1, self.contract, generic_tick_list, False, False, [])

    def create_contract(self, symbol, sec_type="STK", exchange="SMART", currency="USD"):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        return contract

    def tickPrice(self, reqId, tickType, price, attrib):

        self.logger.info(f"Received tick: Type={tickType}, Price={price}")

        # IB sends different types of price updates:
        # 1 = Bid
        # 2 = Ask
        # 4 = Last
        # 6 = High
        # 7 = Low
        # 9 = Close
        if tickType == 4:  # Last price
            self.current_price = price
            self.logger.info(f"Updated current price to: {price}")
            if self.gui:
                self.gui.update_price(price)