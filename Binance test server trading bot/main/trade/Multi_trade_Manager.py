# multi_trade_manager.py

from binance.client import Client
import datetime
import time
from trade.Trade_executor import TradeExecutor

class MultiTradeManager:
    def __init__(self, client: Client, symbols: list, max_positions: int = 3):
        self.client = client
        self.symbols = symbols
        self.max_positions = max_positions
        self.active_positions = {}  # kulcs: szimbólum, érték: TradeExecutor példány

    def can_open_new_position(self):
        return len(self.active_positions) < self.max_positions

    def update_trades(self, signals: dict):
        """
        signals példa:
        {
            'BTCUSDT': 'BUY',
            'ETHUSDT': 'HOLD',
            'LTCUSDT': 'SELL'
        }
        """
        for symbol, signal in signals.items():
            if symbol not in self.symbols:
                continue

            executor = self.active_positions.get(symbol)

            if executor:
                if signal == 'SELL' or signal == 'STOP':
                    executor.close_position()
                    del self.active_positions[symbol]
                else:
                    executor.update_position()  # lehet profit update vagy SL/TP kontroll
            elif signal == 'BUY' and self.can_open_new_position():
                new_executor = TradeExecutor(self.client, symbol)
                new_executor.open_position()
                self.active_positions[symbol] = new_executor

    def summary(self):
        print("[TradeManager] Aktív pozíciók:")
        for symbol, executor in self.active_positions.items():
            print(f"  - {symbol}: {executor.position_summary()}")

