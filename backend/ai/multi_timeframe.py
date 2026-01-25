"""
Multi-Timeframe Analysis
Analyzes multiple timeframes simultaneously for better decision making
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger
from dataclasses import dataclass


@dataclass
class TimeframeSignal:
    """Signal from a specific timeframe"""
    timeframe: str
    action: int  # 0=HOLD, 1=LONG, 2=SHORT, 3=CLOSE
    confidence: float
    regime: str
    trend: str  # UP, DOWN, SIDEWAYS
    strength: int  # 1-3


class MultiTimeframeAnalyzer:
    """
    Analyzes multiple timeframes and provides hierarchical decision making
    
    Timeframe hierarchy (from highest to lowest):
    1. 1d (Daily) - Long-term trend
    2. 4h (4-Hour) - Medium-term trend  
    3. 1h (Hourly) - Short-term trend
    4. 15m (15-Min) - Entry/Exit timing
    
    Rules:
    - Higher timeframe trend takes priority
    - Only trade in direction of higher timeframes
    - Lower timeframes provide entry/exit timing
    """
    
    def __init__(self, exchange_client=None):
        self.exchange_client = exchange_client
        self.timeframes = ['1d', '4h', '1h', '15m']
        self.timeframe_weights = {
            '1d': 0.40,   # Highest weight
            '4h': 0.30,
            '1h': 0.20,
            '15m': 0.10   # Lowest weight (timing only)
        }
    
    def analyze_timeframe(
        self,
        df: pd.DataFrame,
        timeframe: str,
        agent,
        regime_detector,
        market_state: Dict
    ) -> TimeframeSignal:
        """
        Analyze a single timeframe
        
        Returns:
            TimeframeSignal with action, confidence, regime, trend
        """
        try:
            # Get regime
            regime_info = regime_detector.detect_regime(df)
            regime = regime_info['regime']
            confidence = regime_info['confidence']
            
            # Get AI prediction
            ai_action = agent.live_predict(market_state)
            
            # Determine trend
            trend = self._determine_trend(df)
            
            # Calculate signal strength (1-3)
            strength = self._calculate_signal_strength(df, trend, regime)
            
            return TimeframeSignal(
                timeframe=timeframe,
                action=ai_action,
                confidence=confidence,
                regime=regime,
                trend=trend,
                strength=strength
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze {timeframe}: {e}")
            return TimeframeSignal(
                timeframe=timeframe,
                action=0,
                confidence=0.5,
                regime='RANGING',
                trend='SIDEWAYS',
                strength=1
            )
    
    def _determine_trend(self, df: pd.DataFrame) -> str:
        """
        Determine trend direction using multiple indicators
        """
        try:
            latest = df.iloc[-1]
            
            # EMA crossover
            ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
            ema_50 = df['close'].ewm(span=50).mean().iloc[-1] if len(df) >= 50 else ema_20
            
            # MACD
            macd = latest.get('macd', 0)
            signal = latest.get('signal', 0)
            
            # Price vs EMAs
            price = latest['close']
            
            # Count bullish signals
            bullish_signals = 0
            bearish_signals = 0
            
            if price > ema_20:
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            if ema_20 > ema_50:
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            if macd > signal:
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            # Determine trend
            if bullish_signals >= 2:
                return 'UP'
            elif bearish_signals >= 2:
                return 'DOWN'
            else:
                return 'SIDEWAYS'
                
        except Exception as e:
            logger.error(f"Trend determination failed: {e}")
            return 'SIDEWAYS'
    
    def _calculate_signal_strength(self, df: pd.DataFrame, trend: str, regime: str) -> int:
        """
        Calculate signal strength (1-3) based on trend and regime alignment
        """
        strength = 1
        
        # Strong trend + TRENDING regime = strength 3
        if trend in ['UP', 'DOWN'] and regime == 'TRENDING':
            strength = 3
        # Medium trend or ranging with clear direction
        elif trend in ['UP', 'DOWN']:
            strength = 2
        # Sideways = weak
        else:
            strength = 1
        
        return strength
    
    def aggregate_signals(
        self,
        signals: List[TimeframeSignal]
    ) -> Dict:
        """
        Aggregate signals from multiple timeframes
        
        Returns:
            {
                'final_action': int,
                'confidence': float,
                'reasoning': str,
                'timeframe_analysis': dict
            }
        """
        if not signals:
            return {
                'final_action': 0,
                'confidence': 0.5,
                'reasoning': 'No signals available',
                'timeframe_analysis': {}
            }
        
        # Organize signals by timeframe
        signal_dict = {s.timeframe: s for s in signals}
        
        # Check higher timeframe trend alignment
        higher_tf_trend = self._get_higher_timeframe_trend(signal_dict)
        
        # Get entry timing from lower timeframe
        entry_signal = self._get_entry_signal(signal_dict, higher_tf_trend)
        
        # Calculate weighted confidence
        confidence = self._calculate_confidence(signals)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(signal_dict, higher_tf_trend, entry_signal)
        
        return {
            'final_action': entry_signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'timeframe_analysis': {
                tf: {
                    'action': s.action,
                    'trend': s.trend,
                    'regime': s.regime,
                    'strength': s.strength
                }
                for tf, s in signal_dict.items()
            }
        }
    
    def _get_higher_timeframe_trend(self, signal_dict: Dict[str, TimeframeSignal]) -> str:
        """
        Determine the overall trend from higher timeframes
        Priority: 1d > 4h > 1h
        """
        # Check daily first
        if '1d' in signal_dict:
            return signal_dict['1d'].trend
        
        # Then 4h
        if '4h' in signal_dict:
            return signal_dict['4h'].trend
        
        # Then 1h
        if '1h' in signal_dict:
            return signal_dict['1h'].trend
        
        # Fallback to 15m
        if '15m' in signal_dict:
            return signal_dict['15m'].trend
        
        return 'SIDEWAYS'
    
    def _get_entry_signal(
        self,
        signal_dict: Dict[str, TimeframeSignal],
        higher_tf_trend: str
    ) -> int:
        """
        Get entry signal considering higher timeframe trend
        
        Rules:
        - Only LONG if higher TF is UP
        - Only SHORT if higher TF is DOWN
        - Can CLOSE anytime
        - HOLD if conflicting or SIDEWAYS
        """
        # Get lower timeframe signal (15m for timing)
        lower_tf_signal = signal_dict.get('15m')
        
        if not lower_tf_signal:
            return 0  # HOLD
        
        lower_action = lower_tf_signal.action
        
        # Apply higher timeframe filter
        if higher_tf_trend == 'UP':
            # Only allow LONG or CLOSE
            if lower_action == 1:  # LONG
                return 1
            elif lower_action == 3:  # CLOSE
                return 3
            else:
                return 0  # Block SHORT
        
        elif higher_tf_trend == 'DOWN':
            # Only allow SHORT or CLOSE
            if lower_action == 2:  # SHORT
                return 2
            elif lower_action == 3:  # CLOSE
                return 3
            else:
                return 0  # Block LONG
        
        else:  # SIDEWAYS
            # Be more conservative
            if lower_action == 3:  # Always allow CLOSE
                return 3
            
            # Require high confidence for entry in sideways market
            if lower_tf_signal.strength >= 2 and lower_tf_signal.confidence > 0.7:
                return lower_action
            else:
                return 0  # HOLD
    
    def _calculate_confidence(self, signals: List[TimeframeSignal]) -> float:
        """
        Calculate weighted confidence from all timeframes
        """
        if not signals:
            return 0.5
        
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = self.timeframe_weights.get(signal.timeframe, 0.1)
            weighted_confidence += signal.confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_confidence / total_weight
        else:
            return 0.5
    
    def _generate_reasoning(
        self,
        signal_dict: Dict[str, TimeframeSignal],
        higher_tf_trend: str,
        final_action: int
    ) -> str:
        """
        Generate human-readable reasoning
        """
        action_names = ['HOLD', 'LONG', 'SHORT', 'CLOSE']
        final_action_name = action_names[final_action]
        
        # Build reasoning
        parts = []
        
        # Higher timeframe trend
        parts.append(f"Higher TF Trend: {higher_tf_trend}")
        
        # Individual timeframe analysis
        for tf in ['1d', '4h', '1h', '15m']:
            if tf in signal_dict:
                s = signal_dict[tf]
                parts.append(f"{tf}: {s.trend} ({s.regime}, Strength: {s.strength})")
        
        # Final decision
        parts.append(f"Final Decision: {final_action_name}")
        
        return " | ".join(parts)
    
    def should_allow_trade(
        self,
        aggregated_result: Dict,
        min_confidence: float = 0.6
    ) -> bool:
        """
        Determine if trade should be allowed based on multi-timeframe analysis
        """
        # Check confidence
        if aggregated_result['confidence'] < min_confidence:
            return False
        
        # Check action
        action = aggregated_result['final_action']
        if action == 0:  # HOLD
            return False
        
        # Check timeframe alignment
        tf_analysis = aggregated_result.get('timeframe_analysis', {})
        
        # Count aligned timeframes
        aligned = 0
        total = 0
        
        for tf_data in tf_analysis.values():
            if tf_data['action'] == action or tf_data['action'] == 0:
                aligned += 1
            total += 1
        
        # Require at least 50% alignment
        if total > 0 and (aligned / total) >= 0.5:
            return True
        
        return False
