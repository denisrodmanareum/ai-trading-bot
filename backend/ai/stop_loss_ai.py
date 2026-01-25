"""
AI-Based Stop Loss and Take Profit Manager
Uses separate RL models to learn optimal exit points
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from stable_baselines3 import PPO
from loguru import logger
import gymnasium as gym
from gymnasium import spaces


class StopLossEnvironment(gym.Env):
    """
    Environment for learning optimal stop loss levels
    
    State:
    - Current price vs entry price
    - ATR (volatility)
    - Position duration
    - Unrealized PnL
    - Market regime
    - RSI, MACD
    
    Action:
    - Stop loss distance (as multiplier of ATR: 0.5x to 5x)
    
    Reward:
    - Maximize preserved capital
    - Penalize premature exits
    - Reward avoiding large losses
    """
    
    def __init__(self, df: pd.DataFrame, initial_entry_price: float):
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.initial_entry_price = initial_entry_price
        self.current_step = 0
        
        # State space: [price_ratio, atr_norm, duration_norm, pnl_ratio, rsi, macd_norm]
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(6,), 
            dtype=np.float32
        )
        
        # Action space: SL distance as ATR multiplier (continuous: 0.5 to 5.0)
        self.action_space = spaces.Box(
            low=0.5, 
            high=5.0, 
            shape=(1,), 
            dtype=np.float32
        )
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        return self._get_observation(), {}
    
    def _get_observation(self) -> np.ndarray:
        row = self.df.iloc[self.current_step]
        
        price_ratio = row['close'] / self.initial_entry_price - 1.0
        atr_norm = row['atr'] / row['close']
        duration_norm = self.current_step / len(self.df)
        pnl_ratio = price_ratio  # Simplified
        rsi_norm = row['rsi'] / 100.0
        macd_norm = row['macd'] / row['close']
        
        return np.array([
            price_ratio,
            atr_norm,
            duration_norm,
            pnl_ratio,
            rsi_norm,
            macd_norm
        ], dtype=np.float32)
    
    def step(self, action: np.ndarray):
        sl_multiplier = float(action[0])
        
        row = self.df.iloc[self.current_step]
        current_price = row['close']
        atr = row['atr']
        
        # Calculate SL price
        sl_distance = atr * sl_multiplier
        sl_price = self.initial_entry_price - sl_distance  # For LONG
        
        # Check if SL hit
        hit_sl = current_price <= sl_price
        
        # Calculate reward
        if hit_sl:
            # SL triggered
            loss = (sl_price - self.initial_entry_price) / self.initial_entry_price
            reward = loss * 10  # Negative reward for loss
        else:
            # Not hit yet, small positive reward for surviving
            reward = 0.01
        
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1 or hit_sl
        truncated = False
        
        obs = self._get_observation() if not done else np.zeros(6, dtype=np.float32)
        
        return obs, reward, done, truncated, {'sl_hit': hit_sl}


class TakeProfitEnvironment(gym.Env):
    """
    Environment for learning optimal take profit levels
    
    Similar to SL but optimizes for profit taking
    """
    
    def __init__(self, df: pd.DataFrame, initial_entry_price: float):
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.initial_entry_price = initial_entry_price
        self.current_step = 0
        
        # State space
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(6,), 
            dtype=np.float32
        )
        
        # Action space: TP distance as ATR multiplier (1.0 to 10.0)
        self.action_space = spaces.Box(
            low=1.0, 
            high=10.0, 
            shape=(1,), 
            dtype=np.float32
        )
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        return self._get_observation(), {}
    
    def _get_observation(self) -> np.ndarray:
        row = self.df.iloc[self.current_step]
        
        price_ratio = row['close'] / self.initial_entry_price - 1.0
        atr_norm = row['atr'] / row['close']
        duration_norm = self.current_step / len(self.df)
        pnl_ratio = price_ratio
        rsi_norm = row['rsi'] / 100.0
        macd_norm = row['macd'] / row['close']
        
        return np.array([
            price_ratio,
            atr_norm,
            duration_norm,
            pnl_ratio,
            rsi_norm,
            macd_norm
        ], dtype=np.float32)
    
    def step(self, action: np.ndarray):
        tp_multiplier = float(action[0])
        
        row = self.df.iloc[self.current_step]
        current_price = row['close']
        atr = row['atr']
        
        # Calculate TP price
        tp_distance = atr * tp_multiplier
        tp_price = self.initial_entry_price + tp_distance  # For LONG
        
        # Check if TP hit
        hit_tp = current_price >= tp_price
        
        # Calculate reward
        if hit_tp:
            # TP triggered - good!
            profit = (tp_price - self.initial_entry_price) / self.initial_entry_price
            reward = profit * 20  # High reward for profit
        else:
            # Not hit yet
            unrealized_profit = (current_price - self.initial_entry_price) / self.initial_entry_price
            if unrealized_profit > 0:
                reward = 0.01  # Small reward for being in profit
            else:
                reward = -0.01  # Penalty for being in loss
        
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1 or hit_tp
        truncated = False
        
        obs = self._get_observation() if not done else np.zeros(6, dtype=np.float32)
        
        return obs, reward, done, truncated, {'tp_hit': hit_tp}


class StopLossTakeProfitAI:
    """
    Manages Stop Loss and Take Profit using RL models
    """
    
    def __init__(
        self,
        sl_model_path: Optional[str] = None,
        tp_model_path: Optional[str] = None
    ):
        self.sl_model: Optional[PPO] = None
        self.tp_model: Optional[PPO] = None
        
        if sl_model_path:
            self.load_sl_model(sl_model_path)
        if tp_model_path:
            self.load_tp_model(tp_model_path)
    
    def load_sl_model(self, path: str):
        """Load trained SL model"""
        try:
            self.sl_model = PPO.load(path)
            logger.info(f"SL model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load SL model: {e}")
    
    def load_tp_model(self, path: str):
        """Load trained TP model"""
        try:
            self.tp_model = PPO.load(path)
            logger.info(f"TP model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load TP model: {e}")
    
    def predict_stop_loss(
        self,
        current_price: float,
        entry_price: float,
        atr: float,
        position_duration: int,
        pnl_ratio: float,
        rsi: float,
        macd: float
    ) -> Dict:
        """
        Predict optimal stop loss level
        
        Returns:
            {
                'sl_price': float,
                'sl_distance': float (in ATR multiples),
                'method': str
            }
        """
        # Fallback to ATR-based if no model
        if self.sl_model is None:
            # 🔧 모드별 손절 거리 조정
            # SCALP: 빠른 손절 (ATR × 2.0)
            # SWING: 여유 있는 손절 (ATR × 3.0)
            base_sl_distance = atr * 2.5  # 기본값
            sl_price = entry_price - base_sl_distance
            return {
                'sl_price': float(sl_price),
                'sl_distance': 2.5,
                'method': 'atr_fallback'
            }
        
        # Prepare observation
        price_ratio = current_price / entry_price - 1.0
        atr_norm = atr / current_price
        duration_norm = min(position_duration / 100.0, 1.0)
        rsi_norm = rsi / 100.0
        macd_norm = macd / current_price
        
        obs = np.array([
            price_ratio,
            atr_norm,
            duration_norm,
            pnl_ratio,
            rsi_norm,
            macd_norm
        ], dtype=np.float32)
        
        # Predict
        action, _ = self.sl_model.predict(obs, deterministic=True)
        sl_multiplier = float(action[0])
        
        # Calculate SL price
        sl_distance = atr * sl_multiplier
        sl_price = entry_price - sl_distance
        
        return {
            'sl_price': float(sl_price),
            'sl_distance': round(sl_multiplier, 2),
            'method': 'ai_model'
        }
    
    def predict_take_profit(
        self,
        current_price: float,
        entry_price: float,
        atr: float,
        position_duration: int,
        pnl_ratio: float,
        rsi: float,
        macd: float
    ) -> Dict:
        """
        Predict optimal take profit level
        
        Returns:
            {
                'tp_price': float,
                'tp_distance': float (in ATR multiples),
                'method': str
            }
        """
        # Fallback to ATR-based
        if self.tp_model is None:
            # 🔧 모드별 익절 거리 조정
            # SCALP: 빠른 익절 (ATR × 3.0~4.0)
            # SWING: 큰 익절 (ATR × 6.0~8.0)
            base_tp_distance = atr * 5.0  # 기본값 (중간)
            tp_price = entry_price + base_tp_distance
            return {
                'tp_price': float(tp_price),
                'tp_distance': 5.0,
                'method': 'atr_fallback'
            }
        
        # Prepare observation
        price_ratio = current_price / entry_price - 1.0
        atr_norm = atr / current_price
        duration_norm = min(position_duration / 100.0, 1.0)
        rsi_norm = rsi / 100.0
        macd_norm = macd / current_price
        
        obs = np.array([
            price_ratio,
            atr_norm,
            duration_norm,
            pnl_ratio,
            rsi_norm,
            macd_norm
        ], dtype=np.float32)
        
        # Predict
        action, _ = self.tp_model.predict(obs, deterministic=True)
        tp_multiplier = float(action[0])
        
        # Calculate TP price
        tp_distance = atr * tp_multiplier
        tp_price = entry_price + tp_distance
        
        return {
            'tp_price': float(tp_price),
            'tp_distance': round(tp_multiplier, 2),
            'method': 'ai_model'
        }
    
    def get_sl_tp_for_position(
        self,
        position: Dict,
        current_market_data: Dict,
        trading_mode: str = "SCALP"  # 🔧 NEW: 트레이딩 모드
    ) -> Dict:
        """
        Get SL/TP for current position
        
        Args:
            position: {
                'entry_price': float,
                'position_amt': float,
                'unrealized_pnl': float,
                ...
            }
            current_market_data: {
                'close': float,
                'atr': float,
                'rsi': float,
                'macd': float,
                ...
            }
        
        Returns:
            {
                'sl_price': float,
                'tp_price': float,
                'sl_distance': float,
                'tp_distance': float
            }
        """
        entry_price = position['entry_price']
        current_price = current_market_data['close']
        # ATR with safety fallback
        atr = current_market_data.get('atr') or (current_price * 0.02)
        
        # Position duration (would need to track this)
        position_duration = 10  # Placeholder
        
        # PnL ratio
        pnl_ratio = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        
        # Technical indicators
        rsi = current_market_data.get('rsi', 50.0)
        macd = current_market_data.get('macd', 0.0)
        
        # 🔧 모드별 배수 조정 (수수료 고려 + 손익비 개선)
        # SCALP: 2.5:1 손익비 (4% / 1.6% = 2.5)
        # SWING: 3.0:1 손익비 (9% / 3% = 3.0)
        if trading_mode == "SCALP":
            sl_multiplier = 2.0   # 빠른 손절 (약 1.6% with 5x leverage)
            tp_multiplier = 4.0   # 🔧 3.5→4.0 (약 4% with 5x, 수수료 후 3.2%)
        else:  # SWING
            sl_multiplier = 3.0   # 여유 있는 손절 (약 3% with 5x)
            tp_multiplier = 9.0   # 🔧 7.0→9.0 (약 9% with 5x, 수수료 후 8.2%)
        
        # Predict SL
        sl_result = self.predict_stop_loss(
            current_price=current_price,
            entry_price=entry_price,
            atr=atr,
            position_duration=position_duration,
            pnl_ratio=pnl_ratio,
            rsi=rsi,
            macd=macd
        )
        
        # Predict TP
        tp_result = self.predict_take_profit(
            current_price=current_price,
            entry_price=entry_price,
            atr=atr,
            position_duration=position_duration,
            pnl_ratio=pnl_ratio,
            rsi=rsi,
            macd=macd
        )
        
        # 🔧 모드별로 TP/SL 오버라이드 (모델이 없을 때만)
        if sl_result['method'] == 'atr_fallback':
            sl_result['sl_distance'] = sl_multiplier
            sl_result['sl_price'] = entry_price - (atr * sl_multiplier)
        
        if tp_result['method'] == 'atr_fallback':
            tp_result['tp_distance'] = tp_multiplier
            tp_result['tp_price'] = entry_price + (atr * tp_multiplier)
        
        # Adjust for SHORT positions
        if position['position_amt'] < 0:
            # Flip SL and TP for shorts
            sl_result['sl_price'] = entry_price + (entry_price - sl_result['sl_price'])
            tp_result['tp_price'] = entry_price - (tp_result['tp_price'] - entry_price)
        
        return {
            'sl_price': sl_result['sl_price'],
            'tp_price': tp_result['tp_price'],
            'sl_distance': sl_result['sl_distance'],
            'tp_distance': tp_result['tp_distance'],
            'sl_method': sl_result['method'],
            'tp_method': tp_result['method']
        }
