"""
Spike Detector Module
Detects sudden market anomalies:
1. Volume Spikes
2. Volatility Explosions (ATR Ratio)
3. Micro-Acceleration (Candle Expansion)
"""
import pandas as pd
import numpy as np
from loguru import logger

class SpikeDetector:
    def __init__(self, atr_threshold: float = 2.5, volume_threshold_multiplier: float = 2.0):
        self.atr_threshold = atr_threshold
        self.volume_threshold_multiplier = volume_threshold_multiplier
        
    def analyze(self, df_1m: pd.DataFrame, current_1h_atr: float) -> dict:
        """
        Analyze 1m candles for spikes
        
        Args:
            df_1m: DataFrame containing recent 1m candles (at least 20)
            current_1h_atr: Current ATR from 1h timeframe (for context)
            
        Returns:
            dict: {
                "detected": bool,
                "reason": str, # "VOLUME_SPIKE", "VOLATILITY_EXPLOSION", "ACCELERATION", or None
                "score": float # 0.0 to 1.0 severity
            }
        """
        try:
            latest = df_1m.iloc[-1]
            prev = df_1m.iloc[-2]
            
            # 1. Volume Spike Detection
            # Compare current volume to 20-period SMA
            vol_sma = df_1m['volume'].rolling(window=20).mean().iloc[-1]
            is_volume_spike = latest['volume'] > (vol_sma * self.volume_threshold_multiplier)
            
            # 2. Volatility Explosion (ATR Ratio)
            # Compare current 1m Range to 1h ATR (Contextual Volatility)
            # If 1-minute range is huge compared to hourly average range, it's a shock.
            current_range = latest['high'] - latest['low']
            
            # Handle case where ATR is 0 or None
            atr_ratio = 0.0
            if current_1h_atr > 0:
                atr_ratio = current_range / (current_1h_atr / 10.0) # Approx 1h ATR to 1m scale (heuristic /10)
                # Or compare to recent 1m ATR?
                # User config suggested: range_ratio = (high-low) / ATR. 
                # Let's use 1m Range vs 1m ATR if available, or just raw Range vs 1H ATR logic.
                # Let's stick to User's suggestion: "Recent N avg range vs Current range"
                # Let's calculate local 1m ATR
            
            avg_1m_range = (df_1m['high'] - df_1m['low']).rolling(window=20).mean().iloc[-1]
            if avg_1m_range > 0:
                 range_ratio = current_range / avg_1m_range
            else:
                 range_ratio = 0.0
                 
            is_volatility_spike = range_ratio > self.atr_threshold
            
            # 3. Micro-Acceleration (Consecutive Candle Expansion)
            # Check last 3 candles: Body length increasing?
            # Body = abs(Close - Open)
            # Direction must be same (all green or all red)
            bodies = []
            directions = [] 
            for i in range(1, 4): # -1, -2, -3
                row = df_1m.iloc[-i]
                body = abs(row['close'] - row['open'])
                direction = 1 if row['close'] >= row['open'] else -1
                bodies.append(body)
                directions.append(direction)
            
            # bodies[0] is latest, bodies[1] is prev, bodies[2] is prev-prev
            # Acceleration: Latest > Prev > PrevPrev
            is_acceleration = (bodies[0] > bodies[1] > bodies[2]) and \
                              (directions[0] == directions[1] == directions[2]) and \
                              (bodies[0] > avg_1m_range * 1.5) # Significant size
                              
            reason = []
            score = 0.0
            
            if is_volume_spike:
                reason.append("VOLUME")
                score += 0.4
            if is_volatility_spike:
                reason.append("VOLATILITY")
                score += 0.4
            if is_acceleration:
                reason.append("ACCEL")
                score += 0.2
                
            detected = len(reason) > 0
            
            return {
                "detected": detected,
                "reasons": reason, # List of reasons
                "reason_str": "+".join(reason) if reason else "None",
                "score": min(1.0, score),
                "details": {
                    "vol_ratio": float(latest['volume'] / vol_sma) if vol_sma > 0 else 0,
                    "range_ratio": float(range_ratio)
                }
            }

        except Exception as e:
            logger.error(f"Spike Detection Error: {e}")
            return {"detected": False, "reason": "ERROR", "score": 0.0}
