# feedback_gui.py – Bővítve live_trade_log elemzéssel + mainből is futtatható

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys

def run_gui():
    root = tk.Tk()
    app = FeedbackAnalyzerApp(root)
    root.mainloop()

class FeedbackAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" Kereskedési visszacsatolás + live trade elemző")
        self.root.geometry("1100x650")

        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(self.frame)
        self.feedback_tab = ttk.Frame(self.notebook)
        self.live_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.feedback_tab, text="Feedback logok")
        self.notebook.add(self.live_tab, text="Live trade logok")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Feedback log tábla
        self.tree_feedback = ttk.Treeview(self.feedback_tab, columns=("timestamp", "symbol", "predicted_return", "action", "profit"), show="headings")
        for col in self.tree_feedback["columns"]:
            self.tree_feedback.heading(col, text=col)
            self.tree_feedback.column(col, width=100)
        self.tree_feedback.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar1 = ttk.Scrollbar(self.feedback_tab, orient="vertical", command=self.tree_feedback.yview)
        self.tree_feedback.configure(yscroll=scrollbar1.set)
        scrollbar1.pack(side=tk.LEFT, fill=tk.Y)

        # Live trade log tábla
        self.tree_live = ttk.Treeview(self.live_tab, columns=("timestamp", "symbol", "action", "price", "quantity", "profit"), show="headings")
        for col in self.tree_live["columns"]:
            self.tree_live.heading(col, text=col)
            self.tree_live.column(col, width=100)
        self.tree_live.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2 = ttk.Scrollbar(self.live_tab, orient="vertical", command=self.tree_live.yview)
        self.tree_live.configure(yscroll=scrollbar2.set)
        scrollbar2.pack(side=tk.LEFT, fill=tk.Y)

        # Gombok
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(fill=tk.X)
        ttk.Button(self.button_frame, text=" Feedback log betöltés", command=self.load_feedback_logs).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(self.button_frame, text=" Live trade log betöltés", command=self.load_live_logs).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(self.button_frame, text=" Feedback grafikon", command=self.show_feedback_plot).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(self.button_frame, text=" Live profit eloszlás", command=self.show_live_profit_plot).pack(side=tk.LEFT, padx=10, pady=5)

        self.feedback_data = pd.DataFrame()
        self.live_data = pd.DataFrame()

    def load_feedback_logs(self):
        pattern = os.path.join("logs", "feedback_log_*.csv")
        files = glob.glob(pattern)
        all_data = []
        for file in files:
            df = pd.read_csv(file)
            df['file'] = os.path.basename(file)
            all_data.append(df)

        if not all_data:
            messagebox.showerror("Hiba", "Nem található feedback log.")
            return

        self.feedback_data = pd.concat(all_data, ignore_index=True)
        self.feedback_data['timestamp'] = pd.to_datetime(self.feedback_data['timestamp'], errors='coerce')
        self.feedback_data['profit'] = pd.to_numeric(self.feedback_data['profit'], errors='coerce')
        self.feedback_data['predicted_return'] = pd.to_numeric(self.feedback_data['predicted_return'], errors='coerce')

        for row in self.tree_feedback.get_children():
            self.tree_feedback.delete(row)
        for _, row in self.feedback_data.iterrows():
            self.tree_feedback.insert("", "end", values=(row['timestamp'], row['symbol'], f"{row['predicted_return']:.4f}", row['action'], f"{row['profit']:.4f}"))

    def load_live_logs(self):
        pattern = os.path.join("logs", "live_trade_log_*.csv")
        files = glob.glob(pattern)
        all_data = []
        for file in files:
            df = pd.read_csv(file)
            df['file'] = os.path.basename(file)
            df['symbol'] = df['file'].str.replace("live_trade_log_", "").str.replace(".csv", "")
            all_data.append(df)

        if not all_data:
            messagebox.showerror("Hiba", "Nem található live trade log.")
            return

        self.live_data = pd.concat(all_data, ignore_index=True)
        self.live_data['timestamp'] = pd.to_datetime(self.live_data['timestamp'], errors='coerce')

        for row in self.tree_live.get_children():
            self.tree_live.delete(row)
        for _, row in self.live_data.iterrows():
            self.tree_live.insert("", "end", values=(row['timestamp'], row['symbol'], row['action'], row.get('current_price', 'N/A'), row['quantity'], f"{row['profit']:.4f}"))

    def show_feedback_plot(self):
        if self.feedback_data.empty:
            messagebox.showinfo("Figyelem", "Előbb tölts be feedback logokat!")
            return

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.scatter(self.feedback_data['predicted_return'], self.feedback_data['profit'], alpha=0.5, c=(self.feedback_data['profit'] > 0), cmap='bwr')
        ax.axhline(0, color='gray', linestyle='--')
        ax.set_xlabel('Predicted Return')
        ax.set_ylabel('Profit')
        ax.set_title('Predikció és Profit kapcsolata')
        ax.grid(True)

        plot_window = tk.Toplevel(self.root)
        plot_window.title(" Feedback grafikon")
        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def show_live_profit_plot(self):
        if self.live_data.empty:
            messagebox.showinfo("Figyelem", "Előbb tölts be live trade logokat!")
            return

        fig, ax = plt.subplots(figsize=(8, 4))
        for symbol in self.live_data['symbol'].unique():
            symbol_data = self.live_data[self.live_data['symbol'] == symbol]
            ax.hist(symbol_data['profit'], bins=30, alpha=0.5, label=symbol)

        ax.set_xlabel("Profit")
        ax.set_ylabel("Gyakoriság")
        ax.set_title(" Profit eloszlás szimbólumonként")
        ax.legend()
        ax.grid(True)

        plot_window = tk.Toplevel(self.root)
        plot_window.title(" Live trade profit eloszlás")
        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    run_gui()
