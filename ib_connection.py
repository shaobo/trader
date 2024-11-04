from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from datetime import datetime
import logging


class IBConnection(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = {}
        self.is_connected = False
        self.current_price = 0
        self.contract = None
        self.gui = None
        self.symbol = None
        self.logger = logging.getLogger('IBConnection')

    def error(self, reqId, errorCode, errorString):
        self.logger.error(f'Error {errorCode}: {errorString}')
        if self.gui:
            self.gui.update_status(f'Error {errorCode}: {errorString}')

    def connectAck(self):
        self.is_connected = True
        self.logger.info("Connected to IB")
        if self.gui:
            self.gui.update_status("Connected to IB")

    def connectionClosed(self):
        self.is_connected = False
        self.logger.info("Disconnected from IB")
        if self.gui:
            self.gui.update_status("Disconnected from IB")

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
        generic_tick_list = ""  # Request Just basic price data
        self.reqMktData(1, self.contract, generic_tick_list, False, False, [])
