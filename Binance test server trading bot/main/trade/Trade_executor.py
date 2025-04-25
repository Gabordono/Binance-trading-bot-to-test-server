# trade_executor.py

from binance.client import Client
import datetime
import os

class TradeExecutor:
    def __init__(self, client: Client, symbol: str, usd_amount: float = 10.0):
        self.client = client
        self.symbol = symbol
        self.usd_amount = usd_amount
        self.position = None
        self.entry_price = None
        self.quantity = None
        self.sl_threshold = None  # dinamikus lesz
        self.tp_threshold = None
        self.log_file = f"live_trade_log_{symbol}.csv"

        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("timestamp,action,price,quantity,profit\n")

    def get_price(self):
        ticker = self.client.get_symbol_ticker(symbol=self.symbol)
        return float(ticker['price'])

    def calculate_sl_tp(self, current_price):
        sl = 0.005 * current_price  # 0.5% le
        tp = 0.00001 * current_price   # 1% fel
        self.sl_threshold = (current_price - sl) / current_price
        self.tp_threshold = (current_price + tp) / current_price

    def open_position(self):
        price = self.get_price()
        self.calculate_sl_tp(price)
        self.quantity = round(self.usd_amount / price, 6)
        self.client.order_market_buy(symbol=self.symbol, quantity=self.quantity)
        self.entry_price = price
        self.position = "LONG"
        self._log("BUY", price, 0)

    def close_position(self):
        if self.position != "LONG":
            return
        price = self.get_price()
        self.client.order_market_sell(symbol=self.symbol, quantity=self.quantity)
        profit = (price - self.entry_price) * self.quantity
        self._log("SELL", price, profit)
        self.position = None

    def update_position(self):
        if self.position == "LONG":
            current_price = self.get_price()
            if current_price <= self.entry_price * self.sl_threshold:
                print(f"[{self.symbol}] [STOP-LOSS] zárás aktiválva")
                self.close_position()
            elif current_price >= self.entry_price * self.tp_threshold:
                print(f"[{self.symbol}] [TAKE-PROFIT] zárás aktiválva")
                self.close_position()

    def position_summary(self):
        return f"Entry: {self.entry_price}, Qty: {self.quantity}, State: {self.position}"

    def _log(self, action, price, profit):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a') as f:
            f.write(f"{now},{action},{price},{self.quantity},{profit:.4f}\n")
