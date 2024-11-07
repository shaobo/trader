import logging
from ib_connection import IBConnection
from trader import StockTrader
from gui import TradingGUI


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading.log'),
            logging.StreamHandler()
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger('main')

    try:
        # Create instances
        ib = IBConnection()
        # if not ib_connection.connect_and_init():
        #     logger.error("Failed to connect to IB")
        #     return
        trader = StockTrader(ib)
        gui = TradingGUI(trader)

        # Start the application
        logger.info("Starting trading application")
        gui.run()
        ib.connect_and_init()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()