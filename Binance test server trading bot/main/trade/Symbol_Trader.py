# trade/Symbol_Trader.py (SYNC verzió - automatikus pozíció szinkronizálás)

from binance.client import Client
import pandas as pd
from xgboost import XGBRegressor
import numpy as np
import datetime
import os
import json
import math
from prediction.MI_Strategy import MLStrategy



def prepare_features(df):
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['return'] = df['close'].pct_change()
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['volatility'] = df['close'].rolling(window=5).std()
    df['rsi'] = compute_rsi(df['close'], window=14)
    df['target'] = (df['close'].shift(-1) - df['close']) / df['close']
    return df.dropna()


def compute_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def adjust_quantity_to_step(quantity, step_size_str):
    step_size = float(step_size_str)
    precision = int(round(-math.log10(step_size)))
    return round(math.floor(quantity / step_size) * step_size, precision)


with open("config.json", "r") as f:
    config = json.load(f)

fixed_trade_usd = config.get("fixed_trade_usd", 10)
fee_percent = config.get("fee_percent", 0.001)
interval = Client.KLINE_INTERVAL_5MINUTE
limit = 100

positions = {}
entry_prices = {}


def trade_symbol(symbol, client):
    global positions, entry_prices
    log_file = f"logs/live_trade_log_{symbol}.csv"
    feedback_log_file = f"logs/feedback_log_{symbol}.csv"

    if not os.path.exists("logs"):
        os.makedirs("logs")
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write("timestamp,current_price,action,balance,quantity,profit\n")
    if not os.path.exists(feedback_log_file):
        with open(feedback_log_file, 'w') as f:
            f.write("timestamp,symbol,predicted_return,action,profit\n")

    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'])
        df = prepare_features(df)

        current_price = df['close'].iloc[-1]
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        trend_ok = df['ma5'].iloc[-1] > df['ma10'].iloc[-1] and df['rsi'].iloc[-1] < 70
        balance = float(client.get_asset_balance(asset='USDT')['free'])
        asset = symbol.replace("USDT", "")
        asset_balance = float(client.get_asset_balance(asset=asset)['free'])

        symbol_info = client.get_symbol_info(symbol)
        step_size = None
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = f['stepSize']
                break

        quantity = fixed_trade_usd / current_price
        if step_size:
            quantity = adjust_quantity_to_step(quantity, step_size)

        strategy = MLStrategy(client, [symbol])
        sl_percent, tp_percent = strategy.dynamic_sl_tp(current_price, df['volatility'].iloc[-1])

        if symbol not in positions:
            if asset_balance > 0:
                positions[symbol] = "LONG"
                entry_prices[symbol] = current_price
                print(f"[SYNC] {symbol} – pozíció szinkronizálva")
            else:
                positions[symbol] = None
                entry_prices[symbol] = None

        features = ['close', 'return', 'ma5', 'ma10', 'volatility', 'rsi']
        X = df[features].values
        y = df['target'].values
        model = XGBRegressor(n_estimators=30, max_depth=3, learning_rate=0.05)
        model.fit(X, y)
        predicted_return = model.predict(df[features].iloc[-1].values.reshape(1, -1))[0]

        with open(f"logs/prediction_log_{symbol}.csv", 'a') as f:
            f.write(f"{now},{current_price},{predicted_return}\n")

        action = "HOLD"
        profit = 0

        if positions[symbol] == "LONG":
            entry_price = entry_prices[symbol]
            if current_price <= entry_price * (1 - sl_percent):
                client.order_market_sell(symbol=symbol, quantity=asset_balance)
                action = "STOP-LOSS"
                print(f"[EXIT] {symbol} zárva (STOP-LOSS)")
                profit = (current_price * (1 - fee_percent)) - (entry_price * (1 + fee_percent))
                positions[symbol] = None
                entry_prices[symbol] = None
                with open(feedback_log_file, 'a') as f:
                    f.write(f"{now},{symbol},{predicted_return:.6f},{action},{profit:.4f}\n")

            elif current_price >= entry_price * (1 + tp_percent):
                client.order_market_sell(symbol=symbol, quantity=asset_balance)
                action = "TAKE-PROFIT"
                print(f"[EXIT] {symbol} zárva (TAKE-PROFIT)")
                profit = (current_price * (1 - fee_percent)) - (entry_price * (1 + fee_percent))
                positions[symbol] = None
                entry_prices[symbol] = None
                with open(feedback_log_file, 'a') as f:
                    f.write(f"{now},{symbol},{predicted_return:.6f},{action},{profit:.4f}\n")

        elif positions[symbol] is None:
            if trend_ok:
                response = client.order_market_buy(symbol=symbol, quantity=quantity)
                action = "BUY"
                print(f"[BUY] {symbol} nyitva ({quantity})")
                positions[symbol] = "LONG"
                entry_prices[symbol] = current_price

        with open(log_file, 'a') as f:
            f.write(f"{now},{current_price},{action},{balance},{quantity},{profit:.4f}\n")

        print(f"[{symbol}] {now} | Művelet: {action} | Ár: {current_price:.2f} | Profit: {profit:.4f}")

    except Exception as e:
        print(f"[{symbol}] Hiba: {e}")