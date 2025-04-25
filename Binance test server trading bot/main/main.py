
# main.py

import time
import json
import subprocess
import os
from feedback_gui import run_gui
import threading

# GUI és tanulási script automatikus indítása
base = os.path.dirname(__file__)
gui_path = os.path.join(base, "feedback_gui.py")
learning_path = os.path.join(base, "feedback_learning.py")


threading.Thread(target=run_gui, daemon=True).start()
subprocess.Popen(["python", learning_path])


from datetime import datetime, timedelta
from binance.client import Client
from Strategy_Factory import StrategyFactory
from trade.Multi_trade_Manager import MultiTradeManager
from trade.Symbol_Trader import trade_symbol

# --- Konfiguráció betöltése fájlból
with open("config.json", "r") as f:
    config = json.load(f)

api_key = config["api_key"]
api_secret = config["api_secret"]
strategy_name = config["strategy"]
symbols = config["symbols"]
max_positions = config.get("max_positions", 3)
price_check_interval = 60  # 1 perc
decision_interval = config.get("interval_sec", 300)
min_usdt_balance = config.get("min_usdt_balance", 10)  # minimum USDT figyelmeztetés

# --- Binance kliens inicializálása
testnet_url = config.get("api_url", 'https://testnet.binance.vision/api')
client = Client(api_key, api_secret)
client.API_URL = testnet_url

# --- USDT ellenőrzés induláskor
try:
    usdt_balance = float(client.get_asset_balance(asset='USDT')['free'])
    print(f" Elérhető USDT egyenleg: {usdt_balance}")
    if usdt_balance < min_usdt_balance:
        print(f" FIGYELEM: Az USDT egyenleg alacsony (< {min_usdt_balance} USDT). A bot nem biztos, hogy tud kereskedni.")
except Exception as e:
    print(f" Nem sikerült lekérdezni az USDT egyenleget: {e}")

# --- Stratégiabetöltés + kereskedéskezelő
strategy = StrategyFactory(strategy_name, client, symbols).get_strategy()
trade_manager = MultiTradeManager(client, symbols, max_positions=max_positions)

# --- Fő ciklus
log_file = "logs/bot_activity_log.txt"
if not os.path.exists("logs"): os.makedirs("logs")

with open(log_file, 'a') as log:
  log.write(f"[START] Kereskedési bot elindítva – stratégia: {strategy_name.upper()}\n")

next_decision_time = datetime.now()

while True:
    try:
        with open(log_file, 'a') as log:
            now = datetime.now()

        for symbol in symbols:
            trade_symbol(symbol, client)

        if now >= next_decision_time:
            signals = strategy.generate_signals()
            log.write(f"[DÖNTÉS]", signals)
            trade_manager.update_trades(signals)
            trade_manager.summary()
            next_decision_time = now + timedelta(seconds=decision_interval)
        else:
            log.write(f"[VIZSGÁLAT] Árfolyamfigyelés folyamatban... ({now.strftime('%H:%M:%S')})")

        log.write("\n")
        time.sleep(price_check_interval)

    except Exception as e:
     with open(log_file, 'a') as log:
      log.write(f"[HIBA] {e}\n")
    time.sleep(60)
