import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox
import threading
import logging


class TradingGUI:
    def __init__(self, trader):
        self.trader = trader
        self.trader.ib.gui = self
        self.root = tk.Tk()
        self.root.title("Stock Trading Bot")
        self.logger = logging.getLogger('TradingGUI')
        self.setup_gui()

    def setup_gui(self):
        # Create main container with padding
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Style configuration
        style = ttk.Style()
        style.configure('Status.TLabel', foreground='blue')
        style.configure('Price.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')

        self.create_connection_section()
        self.create_stock_section()
        self.create_price_section()
        self.create_trading_section()
        self.create_position_section()
        self.create_log_section()

    def create_connection_section(self):
        frame = ttk.LabelFrame(self.main_frame, text="Connection", padding="5")
        frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.connect_btn = ttk.Button(frame, text="Connect to IB", command=self.connect_to_ib)
        self.connect_btn.grid(row=0, column=0, padx=5)

        self.status_label = ttk.Label(frame, text="Disconnected", style='Status.TLabel')
        self.status_label.grid(row=0, column=1, padx=5)

    def create_stock_section(self):
        frame = ttk.LabelFrame(self.main_frame, text="Stock Settings", padding="5")
        frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(frame, text="Symbol:").grid(row=0, column=0, padx=5)
        self.symbol_var = tk.StringVar(value="TSLA")
        self.symbol_entry = ttk.Entry(frame, textvariable=self.symbol_var, width=10)
        self.symbol_entry.grid(row=0, column=1, padx=5)

        ttk.Button(frame, text="Set Symbol", command=self.set_symbol).grid(row=0, column=2, padx=5)

    def create_price_section(self):
        frame = ttk.LabelFrame(self.main_frame, text="Price Information", padding="5")
        frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Reference price controls
        ttk.Label(frame, text="Reference Price:").grid(row=0, column=0, padx=5)
        self.ref_price_var = tk.StringVar()
        self.ref_price_entry = ttk.Entry(frame, textvariable=self.ref_price_var, width=10)
        self.ref_price_entry.grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Set", command=self.set_reference_price).grid(row=0, column=2, padx=5)

        # Current price display
        ttk.Label(frame, text="Current Price:").grid(row=1, column=0, padx=5)
        self.current_price_label = ttk.Label(frame, text="0.00", style='Price.TLabel')
        self.current_price_label.grid(row=1, column=1, padx=5)

    def create_trading_section(self):
        frame = ttk.LabelFrame(self.main_frame, text="Trading Controls", padding="5")
        frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.start_btn = ttk.Button(frame, text="Start Trading", command=self.start_trading)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(frame, text="Stop Trading", command=self.stop_trading, state='disabled')
        self.stop_btn.grid(row=0, column=1, padx=5)

    def create_position_section(self):
        frame = ttk.LabelFrame(self.main_frame, text="Positions", padding="5")
        frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.position_text = tk.Text(frame, height=5, width=50)
        self.position_text.grid(row=0, column=0, padx=5)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.position_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.position_text.configure(yscrollcommand=scrollbar.set)

    def create_log_section(self):
        frame = ttk.LabelFrame(self.main_frame, text="Log", padding="5")
        frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.log_text = tk.Text(frame, height=6, width=50)
        self.log_text.grid(row=0, column=0, padx=5)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def connect_to_ib(self):
        try:
            self.trader.ib.connect("127.0.0.1", 7497, 1)
            threading.Thread(target=self.trader.ib.run).start()
            self.update_status("Connecting to IB...")
            self.connect_btn.configure(state='disabled')
        except Exception as e:
            self.update_status(f"Connection error: {str(e)}", error=True)

    def set_symbol(self):
        symbol = self.symbol_var.get().strip().upper()
        if symbol:
            self.trader.ib.symbol = symbol
            self.trader.ib.start_price_stream(symbol)
            self.log_message(f"Started price stream for {symbol}")
        else:
            messagebox.showerror("Error", "Please enter a valid symbol")

    def set_reference_price(self):
        try:
            price = float(self.ref_price_var.get())
            if price <= 0:
                raise ValueError("Price must be positive")
            self.trader.set_reference_price(price)
            self.log_message(f"Reference price set to: {price}")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def start_trading(self):
        if not self.trader.ib.is_connected:
            messagebox.showerror("Error", "Please connect to IB first")
            return
        if self.trader.reference_price <= 0:
            messagebox.showerror("Error", "Please set reference price first")
            return

        self.trader.start_trading()
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.log_message("Trading started")

    def stop_trading(self):
        self.trader.stop_trading()
        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.log_message("Trading stopped")

    def update_status(self, message, error=False):
        style = 'Error.TLabel' if error else 'Status.TLabel'
        self.status_label.configure(text=message, style=style)
        self.log_message(message)

    def update_price(self, price):
        self.current_price_label.configure(text=f"{price:.2f}")
        self.update_positions()

    def update_positions(self):
        self.position_text.delete(1.0, tk.END)
        for pos in self.trader.positions:
            self.position_text.insert(tk.END,
                                      f"Shares: {pos['shares']}, Price: {pos['price']:.2f}, Time: {pos['time'].strftime('%H:%M:%S')}\n")

    def log_message(self, message):
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')}: {message}\n")
        self.log_text.see(tk.END)

    def run(self):
        self.root.mainloop()