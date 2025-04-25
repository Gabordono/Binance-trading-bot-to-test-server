# ml_strategy.py

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from binance.client import Client
from collections import Counter
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import TimeSeriesSplit
import json
import os

class MLStrategy:
    def __init__(self, client: Client, symbols: list):
        self.client = client
        self.symbols = symbols
        self.timeframes = [Client.KLINE_INTERVAL_5MINUTE]
        self.limit = 100
        self.param_dir = "params"
        os.makedirs(self.param_dir, exist_ok=True)

    def fetch_klines(self, symbol, interval):
        klines = self.client.get_klines(symbol=symbol, interval=interval, limit=self.limit)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def prepare_features(self, df):
        df['return'] = df['close'].pct_change()
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['volatility'] = df['close'].rolling(window=5).std()
        df['rsi'] = self.compute_rsi(df['close'], window=14)

        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26

        # Bollinger szalag
        df['bollinger_middle'] = df['close'].rolling(window=20).mean()
        df['bollinger_std'] = df['close'].rolling(window=20).std()
        df['bollinger_upper'] = df['bollinger_middle'] + 2 * df['bollinger_std']
        df['bollinger_lower'] = df['bollinger_middle'] - 2 * df['bollinger_std']

        # Stochastic Oscillator
        low14 = df['low'].rolling(window=14).min()
        high14 = df['high'].rolling(window=14).max()
        df['stochastic_k'] = 100 * ((df['close'] - low14) / (high14 - low14))

        # Új indikátorok
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['momentum'] = df['close'] - df['close'].shift(10)

        df['target'] = (df['close'].shift(-1) - df['close']) / df['close']
        return df.dropna()

    def compute_rsi(self, series, window=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def dynamic_sl_tp(self, price, volatility):
        sl = volatility * 1.2
        tp = volatility * 2.0
        return round(sl, 5), round(tp, 5)

    def generate_signals(self):
        signals = {}
        for symbol in self.symbols:
            df = self.fetch_klines(symbol, self.timeframes[0])
            df = self.prepare_features(df)
            features = ['close', 'return', 'ma5', 'ma10', 'volatility', 'rsi',
                        'macd', 'bollinger_middle', 'bollinger_upper', 'bollinger_lower',
                        'stochastic_k', 'ema20', 'momentum']
            X = df[features].values
            y = df['target'].values

            if len(X) < 20:
                signals[symbol] = 'HOLD'
                continue

            param_file = os.path.join(self.param_dir, f"best_params_{symbol}.json")
            if os.path.exists(param_file):
                with open(param_file, 'r') as f:
                    best_params = json.load(f)
                print(f"[{symbol}] Betöltött hiperparaméterek: {best_params}")
                model = XGBRegressor(**best_params)
                model.fit(X[:-1], y[:-1])
            else:
                param_grid = {
                    'n_estimators': [50, 100],
                    'max_depth': [3, 4, 5],
                    'learning_rate': [0.03, 0.05, 0.1]
                }
                tscv = TimeSeriesSplit(n_splits=3)
                search = GridSearchCV(XGBRegressor(), param_grid, cv=tscv, scoring='neg_mean_squared_error', verbose=0)
                search.fit(X[:-1], y[:-1])
                model = search.best_estimator_
                best_params = search.best_params_
                print(f"[{symbol}] Legjobb hiperparaméterek: {best_params}")
                with open(param_file, 'w') as f:
                    json.dump(best_params, f, indent=4)

            prediction = model.predict([X[-1]])[0]

            if prediction > 0.0005:
                signals[symbol] = 'BUY'
            elif prediction < -0.0005:
                signals[symbol] = 'SELL'
            else:
                signals[symbol] = 'HOLD'

        return signals
