# signal_generator.py

import pandas as pd
from binance.client import Client
import numpy as np

class SignalGenerator:
    def __init__(self, client: Client, symbols: list, interval: str = Client.KLINE_INTERVAL_5MINUTE, limit: int = 100):
        self.client = client
        self.symbols = symbols
        self.interval = interval
        self.limit = limit

    def fetch_klines(self, symbol):
        klines = self.client.get_klines(symbol=symbol, interval=self.interval, limit=self.limit)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        return df

    def compute_rsi(self, series, window=14):
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self):
        signals = {}
        for symbol in self.symbols:
            df = self.fetch_klines(symbol)
            df['rsi'] = self.compute_rsi(df['close'])
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()

            latest = df.iloc[-1]
            if latest['ma5'] > latest['ma10'] and latest['rsi'] < 70:
                signals[symbol] = 'BUY'
            elif latest['rsi'] > 80:
                signals[symbol] = 'SELL'
            else:
                signals[symbol] = 'HOLD'
        return signals

