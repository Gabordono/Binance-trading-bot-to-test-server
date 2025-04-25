
# asset_checker.py

from binance.client import Client
import json

# Konfiguráció betöltése
with open("config.json", "r") as f:
    config = json.load(f)

api_key = config["api_key"]
api_secret = config["api_secret"]
api_url = config.get("api_url", "https://testnet.binance.vision/api")

client = Client(api_key, api_secret)
client.API_URL = api_url

# Lekérdezhető eszközök
assets_to_check = ["USDT", "BTC", "ETH", "BNB", "LTC"]

print("💰 Binance Spot Testnet – Egyenlegellenőrzés:\n")
for asset in assets_to_check:
    try:
        balance = client.get_asset_balance(asset=asset)
        free = float(balance['free'])
        locked = float(balance['locked'])
        print(f"{asset}: Szabad = {free:.4f}, Lekötött = {locked:.4f}")
    except Exception as e:
        print(f"{asset}: ⚠️ Hiba – {e}")
