# strategy_factory.py

from Signal_Generator import SignalGenerator
from prediction.MI_Strategy import MLStrategy

class StrategyFactory:
    def __init__(self, strategy_name, client, symbols):
        self.strategy_name = strategy_name.lower()
        self.client = client
        self.symbols = symbols

    def get_strategy(self):
        if self.strategy_name == "rsi_ma":
            return SignalGenerator(self.client, self.symbols)
        elif self.strategy_name == "ml":
            return MLStrategy(self.client, self.symbols)
        else:
            raise ValueError(f"Ismeretlen stratégia: {self.strategy_name}")


