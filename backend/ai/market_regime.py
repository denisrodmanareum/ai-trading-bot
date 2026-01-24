"""
Market Regime Detection
Classifies market conditions: Trending, Ranging, High Volatility
"""
import numpy as np
import pandas as pd
from typing import Dict, Literal
from loguru import logger


MarketRegime = Literal["TRENDING", "RANGING", "HIGH_VOLATILITY"]


class MarketRegimeDetector:
    """
    Detect market regime using technical indicators
    - ADX (Average Directional Index) for trend strength
    - ATR/Price ratio for volatility
    - Price action patterns
    """
    
    def __init__(
        self,
        adx_threshold: float = 25.0,
        volatility_threshold: float = 0.025,
        ranging_bb_threshold: float = 0.02
    ):
        self.adx_threshold = adx_threshold
        self.volatility_threshold = volatility_threshold
        self.ranging_bb_threshold = ranging_bb_threshold
        
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average Directional Index
        ADX > 25: Strong trend
        ADX < 20: Weak trend / Ranging
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smoothed values
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=period).mean()
        
        return float(adx.iloc[-1]) if not adx.empty else 0.0
    
    def calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Calculate normalized volatility (ATR / Close)
        """
        if 'atr' in df.columns and 'close' in df.columns:
            atr = df['atr'].iloc[-1]
            close = df['close'].iloc[-1]
            return float(atr / close) if close > 0 else 0.0
        return 0.0
    
    def calculate_bb_width(self, df: pd.DataFrame) -> float:
        """
        Calculate Bollinger Band width (normalized)
        Narrow bands indicate ranging market
        """
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'close' in df.columns:
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            close = df['close'].iloc[-1]
            
            bb_width = (bb_upper - bb_lower) / close if close > 0 else 0
            return float(bb_width)
        return 0.0
    
    def detect_regime(self, df: pd.DataFrame) -> Dict:
        """
        Detect current market regime
        
        Returns:
            {
                'regime': str,
                'confidence': float,
                'metrics': dict
            }
        """
        try:
            # Calculate indicators
            adx = self.calculate_adx(df)
            volatility = self.calculate_volatility(df)
            bb_width = self.calculate_bb_width(df)
            
            # Classify regime
            regime = self._classify_regime(adx, volatility, bb_width)
            confidence = self._calculate_confidence(adx, volatility, bb_width)
            
            result = {
                'regime': regime,
                'confidence': confidence,
                'metrics': {
                    'adx': adx,
                    'volatility': volatility,
                    'bb_width': bb_width
                },
                'strategy_params': self.get_strategy_params(regime)
            }
            
            logger.info(f"Market Regime: {regime} (ADX: {adx:.2f}, Vol: {volatility:.4f}, Conf: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to detect market regime: {e}")
            return {
                'regime': 'RANGING',  # Default to conservative
                'confidence': 0.5,
                'metrics': {},
                'strategy_params': self.get_strategy_params('RANGING')
            }
    
    def _classify_regime(self, adx: float, volatility: float, bb_width: float) -> MarketRegime:
        """
        Classify market regime based on indicators
        
        Priority:
        1. High Volatility (if vol > threshold)
        2. Trending (if ADX > threshold)
        3. Ranging (default)
        """
        # High volatility takes priority
        if volatility > self.volatility_threshold:
            return "HIGH_VOLATILITY"
        
        # Strong trend
        if adx > self.adx_threshold:
            return "TRENDING"
        
        # Ranging / consolidation
        return "RANGING"
    
    def _calculate_confidence(self, adx: float, volatility: float, bb_width: float) -> float:
        """
        Calculate confidence in regime classification (0-1)
        """
        # Normalize indicators
        adx_score = min(adx / 50.0, 1.0)  # ADX maxes at ~50
        vol_score = min(volatility / 0.05, 1.0)  # 5% vol is high
        bb_score = min(bb_width / 0.04, 1.0)  # 4% BB width
        
        # Average confidence
        confidence = (adx_score + vol_score + bb_score) / 3.0
        return float(np.clip(confidence, 0.3, 1.0))  # Min 30% confidence
    
    def get_strategy_params(self, regime: MarketRegime) -> Dict:
        """
        Get recommended strategy parameters for each regime
        """
        params = {
            "TRENDING": {
                "min_signal_strength": 2,     # Allow mid-strength signals
                "leverage_multiplier": 1.2,   # Increase leverage in trends
                "stop_loss_atr_mult": 2.0,    # Wider stops
                "take_profit_atr_mult": 4.0,  # Larger targets
                "allow_ai_first": True,       # AI can initiate trades
                "trade_frequency": "normal"
            },
            "RANGING": {
                "min_signal_strength": 3,     # Only strong signals
                "leverage_multiplier": 0.7,   # Reduce leverage
                "stop_loss_atr_mult": 1.5,    # Tighter stops
                "take_profit_atr_mult": 2.5,  # Smaller targets
                "allow_ai_first": False,      # Require technical confirmation
                "trade_frequency": "low"
            },
            "HIGH_VOLATILITY": {
                "min_signal_strength": 3,     # Very strong signals only
                "leverage_multiplier": 0.5,   # Low leverage for safety
                "stop_loss_atr_mult": 2.5,    # Wide stops (avoid whipsaws)
                "take_profit_atr_mult": 3.0,  # Quick exits
                "allow_ai_first": False,      # Conservative
                "trade_frequency": "very_low"
            }
        }
        
        return params.get(regime, params["RANGING"])
    
    def should_trade(self, regime: MarketRegime, signal_strength: int) -> bool:
        """
        Determine if trading is allowed based on regime and signal strength
        """
        params = self.get_strategy_params(regime)
        return signal_strength >= params["min_signal_strength"]
    
    def adjust_leverage(self, base_leverage: int, regime: MarketRegime, symbol: str = "BTCUSDT") -> int:
        """
        Adjust leverage based on market regime and coin type
        - Core coins (BTC, ETH, SOL, BNB): Max 10x
        - Other coins: Max 5x
        """
        params = self.get_strategy_params(regime)
        adjusted = int(base_leverage * params["leverage_multiplier"])
        
        # Determine max leverage based on coin type
        core_coins = ['BTC', 'ETH', 'SOL', 'BNB']
        is_core_coin = any(symbol.startswith(coin) for coin in core_coins)
        max_leverage = 10 if is_core_coin else 5
        
        # Safety limits
        adjusted = max(1, min(adjusted, max_leverage))
        
        return adjusted
