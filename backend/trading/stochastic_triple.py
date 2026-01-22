import pandas as pd
from ta.momentum import StochasticOscillator

class StochasticTriple:
    """
    Stochastic Triple Indicator Calculator
    Calculates 3 sets of Stochastic Oscillators:
    1. Fast: 5-3-3 (Scalping)
    2. Mid: 10-6-6 (Day Trading)
    3. Slow: 20-12-12 (Swing)
    """

    def __init__(self, high, low, close):
        self.high = high
        self.low = low
        self.close = close

    def calculate(self):
        """Calculate all stochastic values"""
        return {
            "fast": self._calculate_stoch(window=5, smooth_window=3),
            "mid": self._calculate_stoch(window=10, smooth_window=6),
            "slow": self._calculate_stoch(window=20, smooth_window=12)
        }

    def _calculate_stoch(self, window, smooth_window):
        """Calculate single stochastic oscillator"""
        stoch = StochasticOscillator(
            high=self.high,
            low=self.low,
            close=self.close,
            window=window,
            smooth_window=smooth_window
        )
        return {
            "k": stoch.stoch(),
            "d": stoch.stoch_signal()
        }
