# feedback_learning.py
# Ez a szkript betölti a visszacsatolási naplókat, és elemzéseket végez rajtuk.

import pandas as pd
import os
import glob
import matplotlib.pyplot as plt

# --- Paraméterek ---
log_dir = "logs"
pattern = os.path.join(log_dir, "feedback_log_*.csv")
files = glob.glob(pattern)

all_data = []

# --- Összes visszacsatolási log beolvasása ---
for file in files:
    df = pd.read_csv(file)
    df['file'] = os.path.basename(file)
    all_data.append(df)

# --- Egyesítés ---
if all_data:
    data = pd.concat(all_data, ignore_index=True)
else:
    print(" Nem található feedback_log fájl.")
    exit()

# --- Adattípusok és hibakezelés ---
data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
data['profit'] = pd.to_numeric(data['profit'], errors='coerce')
data['predicted_return'] = pd.to_numeric(data['predicted_return'], errors='coerce')

# --- Alap statisztika ---
print("\n--- Általános statisztika ---")
print(data.describe())

# --- Nyertes vs vesztes kereskedések ---
data['outcome'] = data['profit'].apply(lambda x: 'WIN' if x > 0 else 'LOSS')
print("\n Nyertes / vesztes arány:")
print(data['outcome'].value_counts())

# --- Predikció és profit kapcsolat ---
plt.figure(figsize=(10,6))
plt.scatter(data['predicted_return'], data['profit'], alpha=0.5, c=(data['profit'] > 0), cmap='bwr')
plt.axhline(0, color='gray', linestyle='--')
plt.xlabel('Predicted Return')
plt.ylabel('Profit')
plt.title(' Predikció és profit kapcsolata')
plt.grid(True)
plt.show()

# --- Szimbólumonkénti átlag profit ---
avg_profit_by_symbol = data.groupby("symbol")["profit"].mean().sort_values(ascending=False)
print("\n Átlag profit szimbólumonként:")
print(avg_profit_by_symbol)

# --- Predikció küszöb teszt (pl. > 0.002 esetén) ---
thresh = 0.002
filtered = data[data['predicted_return'] > thresh]
print(f"\n Predikció > {thresh} esetén átlag profit: {filtered['profit'].mean():.4f}")
print(f"Találatok száma: {len(filtered)} / {len(data)}")

