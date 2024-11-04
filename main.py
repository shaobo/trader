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
        ib_connection = IBConnection()
        trader = StockTrader(ib_connection)
        gui = TradingGUI(trader)

        # Start the application
        logger.info("Starting trading application")
        gui.run()
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise


if __name__ == "__main__":
    main()