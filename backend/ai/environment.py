"""
Enhanced Trading Environment with Stochastic Triple Indicators
스토캐스틱 3형제 통합 버전
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional
from loguru import logger

from app.core.config import settings
from ai.rewards import get_reward_strategy


class TradingEnvironment(gym.Env):
    """
    Enhanced Trading Environment with Stochastic Triple
    
    State Space (Extended):
        - Price data (OHLCV)
        - Technical indicators (RSI, MACD, Bollinger Bands, ATR)
        - Stochastic Triple (5-3-3, 10-6-6, 20-12-12) ← NEW
        - Position information
        - Account balance
        
    Action Space:
        - 0: Hold
        - 1: Long (Buy)
        - 2: Short (Sell)
        - 3: Close Position
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        leverage: int = 5,
        commission: float = 0.0004,
        max_position_size: float = 0.1,
        reward_strategy: str = "improved",  # Changed to improved
        use_stochastic: bool = True  # NEW
    ):
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.commission = commission
        self.max_position_size = max_position_size
        self.reward_calculator = get_reward_strategy(reward_strategy)
        self.use_stochastic = use_stochastic
        
        # Calculate number of features
        base_features = 12  # Original features
        stoch_features = 6 if use_stochastic else 0  # 6 stochastic values
        self.n_features = base_features + stoch_features
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.n_features,),
            dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(4)
        
        # Episode variables
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0
        self.position_size = 0.0
        self.entry_price = 0.0
        # Track entry fee so we can compute trade PnL without double-counting
        self.entry_fee = 0.0
        # Track previous price for mark-to-market PnL
        self.prev_price = float(self.df.iloc[0]['close']) if len(self.df) > 0 else 0.0
        self.max_balance = initial_balance
        self.total_trades = 0
        self.winning_trades = 0
        
        # History
        self.balance_history = []
        self.action_history = []
        self.trade_history = []
        self.current_trade_duration = 0
        self.total_fees = 0.0
        
        # Add stochastic indicators if not present
        if use_stochastic and 'stoch_k_fast' not in df.columns:
            self._add_stochastic_indicators()
    
    def _add_stochastic_indicators(self):
        """
        Add Stochastic Triple indicators to dataframe
        스토캐스틱 3형제 계산
        """
        logger.info("Adding Stochastic Triple indicators...")
        
        # Fast Stochastic (5-3-3)
        self.df['stoch_k_fast'] = self._calculate_stochastic(5, 3)
        self.df['stoch_d_fast'] = self.df['stoch_k_fast'].rolling(3).mean()
        
        # Mid Stochastic (10-6-6)
        self.df['stoch_k_mid'] = self._calculate_stochastic(10, 6)
        self.df['stoch_d_mid'] = self.df['stoch_k_mid'].rolling(6).mean()
        
        # Slow Stochastic (20-12-12)
        self.df['stoch_k_slow'] = self._calculate_stochastic(20, 12)
        self.df['stoch_d_slow'] = self.df['stoch_k_slow'].rolling(12).mean()
        
        # Fill NaN values
        self.df = self.df.bfill().ffill()  # Use bfill() and ffill() instead of deprecated method
        self.df.fillna(50.0, inplace=True)  # Default to neutral
        
        logger.info("✅ Stochastic Triple indicators added")
    
    def _calculate_stochastic(self, k_period: int, smooth: int) -> pd.Series:
        """Calculate %K for stochastic oscillator"""
        low_min = self.df['low'].rolling(window=k_period).min()
        high_max = self.df['high'].rolling(window=k_period).max()
        
        k = 100 * (self.df['close'] - low_min) / (high_max - low_min)
        k_smooth = k.rolling(window=smooth).mean()
        
        return k_smooth
    
    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """Reset the environment"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_fee = 0.0
        self.prev_price = float(self.df.iloc[0]['close']) if len(self.df) > 0 else 0.0
        self.max_balance = self.initial_balance
        self.total_trades = 0
        self.winning_trades = 0
        
        self.balance_history = [self.balance]
        self.action_history = []
        self.trade_history = []
        self.current_trade_duration = 0
        self.total_fees = 0.0
        self.reward_calculator.reset()
        
        return self._get_observation(), {}
    
    def _get_observation(self) -> np.ndarray:
        """
        Get current observation with optional stochastic indicators
        스토캐스틱 포함 관찰값
        """
        row = self.df.iloc[self.current_step]
        
        # Calculate unrealized PnL
        unrealized_pnl = 0.0
        if self.position != 0:
            current_price = float(row['close'])
            if self.position == 1:
                unrealized_pnl = (current_price - self.entry_price) * self.position_size
            else:
                unrealized_pnl = (self.entry_price - current_price) * self.position_size
        
        # Base observation (12 features)
        obs_base = [
            float(row['close']),
            float(row['volume']),
            float(row['rsi']),
            float(row['macd']),
            float(row['signal']),
            float(row['bb_upper']),
            float(row['bb_lower']),
            float(row['atr']),
            float(self.position),
            float(self.position_size),
            float(self.entry_price),
            float(unrealized_pnl)
        ]
        
        # Add stochastic indicators if enabled (6 features)
        if self.use_stochastic:
            obs_stoch = [
                float(row.get('stoch_k_fast', 50.0)),
                float(row.get('stoch_d_fast', 50.0)),
                float(row.get('stoch_k_mid', 50.0)),
                float(row.get('stoch_d_mid', 50.0)),
                float(row.get('stoch_k_slow', 50.0)),
                float(row.get('stoch_d_slow', 50.0))
            ]
            obs = np.array(obs_base + obs_stoch, dtype=np.float32)
        else:
            obs = np.array(obs_base, dtype=np.float32)
        
        # Handle NaN/Inf values
        obs = np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6)
        
        return obs
    
    def get_stochastic_signal(self) -> Dict:
        """
        Get trading signal from stochastic triple
        스토캐스틱 3형제 신호 분석
        """
        if not self.use_stochastic:
            return {"signal": "NEUTRAL", "strength": 0}
        
        row = self.df.iloc[self.current_step]
        
        k_fast = float(row.get('stoch_k_fast', 50.0))
        k_mid = float(row.get('stoch_k_mid', 50.0))
        k_slow = float(row.get('stoch_k_slow', 50.0))
        
        # Oversold (바닥) - BUY signal
        oversold_count = sum([
            k_fast < 20,
            k_mid < 20,
            k_slow < 20
        ])
        
        # Overbought (천장) - SELL signal
        overbought_count = sum([
            k_fast > 80,
            k_mid > 80,
            k_slow > 80
        ])
        
        if oversold_count == 3:
            return {"signal": "STRONG_BUY", "strength": 3}
        elif oversold_count == 2:
            return {"signal": "BUY", "strength": 2}
        elif oversold_count == 1:
            return {"signal": "WEAK_BUY", "strength": 1}
        elif overbought_count == 3:
            return {"signal": "STRONG_SELL", "strength": 3}
        elif overbought_count == 2:
            return {"signal": "SELL", "strength": 2}
        elif overbought_count == 1:
            return {"signal": "WEAK_SELL", "strength": 1}
        else:
            return {"signal": "NEUTRAL", "strength": 0}
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one step in the environment"""
        current_price = float(self.df.iloc[self.current_step]['close'])
        
        # Execute action
        step_pnl = 0.0

        # Mark-to-market: reflect unrealized PnL changes each step.
        # Without this, the agent only sees entry fees (negative) and sparse rewards on close,
        # which often learns "never trade" as the best policy.
        if self.position != 0 and self.position_size > 0:
            price_delta = current_price - float(self.prev_price)
            direction = 1.0 if self.position == 1 else -1.0
            mtm_pnl = price_delta * self.position_size * direction
            if mtm_pnl != 0:
                self.balance += mtm_pnl
                self.max_balance = max(self.max_balance, self.balance)
                step_pnl += mtm_pnl
        
        if action == 1:  # Long
            step_pnl += self._execute_long(current_price)
        elif action == 2:  # Short
            step_pnl += self._execute_short(current_price)
        elif action == 3:  # Close position
            step_pnl += self._close_position(current_price)

        # Update previous price for next step (after any action)
        self.prev_price = current_price
        
        # Move to next step
        self.current_step += 1
        
        if self.position != 0:
            self.current_trade_duration += 1
        
        # Check if episode is done
        done = self.current_step >= len(self.df) - 1
        truncated = self.balance <= 0
        
        # Record history
        self.balance_history.append(self.balance)
        self.action_history.append(action)
        
        # Get next observation
        obs = self._get_observation() if not done and not truncated else np.zeros(self.n_features)
        
        # Get stochastic signal (used for both info and light reward shaping)
        stoch_signal = self.get_stochastic_signal()

        # Base reward from configured strategy
        reward = self.reward_calculator.calculate(
            action=action,
            pnl=step_pnl,
            position_size=self.position_size,
            balance=self.balance
        )

        # Light reward shaping to avoid degenerate "never enter" policies:
        # - Penalize invalid CLOSE when flat
        # - Encourage taking LONG/SHORT when stochastic indicates a signal (only when flat)
        shaping = 0.0
        if action == 3 and self.position == 0:
            shaping -= 0.0001

        if self.position == 0:
            sig = stoch_signal.get("signal", "NEUTRAL")
            strength = float(stoch_signal.get("strength", 0))
            if sig in ("WEAK_BUY", "BUY", "STRONG_BUY"):
                if action == 1:
                    shaping += 0.0002 * strength
                elif action in (0, 2, 3):
                    shaping -= 0.00005 * strength
            elif sig in ("WEAK_SELL", "SELL", "STRONG_SELL"):
                if action == 2:
                    shaping += 0.0002 * strength
                elif action in (0, 1, 3):
                    shaping -= 0.00005 * strength

        reward = float(np.clip(reward + shaping, -10, 10))
        
        info = {
            'balance': self.balance,
            'position': self.position,
            'total_trades': self.total_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'stochastic_signal': stoch_signal  # NEW
        }
        
        return obs, reward, done, truncated, info
    
    def _execute_long(self, price: float) -> float:
        """Execute long position"""
        pnl_change = 0.0
        
        if self.position == -1:
            pnl_change += self._close_position(price)
        
        if self.position == 0:
            max_size = self.balance * self.max_position_size * self.leverage
            self.position_size = max_size / price
            self.entry_price = price
            self.position = 1
            
            commission_cost = max_size * self.commission
            self.balance -= commission_cost
            self.total_fees += commission_cost
            self.entry_fee = commission_cost
            pnl_change -= commission_cost
            self.prev_price = price
            
            logger.debug(f"Long: {self.position_size:.4f} @ {price:.2f}")
        
        return pnl_change
    
    def _execute_short(self, price: float) -> float:
        """Execute short position"""
        pnl_change = 0.0
        
        if self.position == 1:
            pnl_change += self._close_position(price)
        
        if self.position == 0:
            max_size = self.balance * self.max_position_size * self.leverage
            self.position_size = max_size / price
            self.entry_price = price
            self.position = -1
            
            commission_cost = max_size * self.commission
            self.balance -= commission_cost
            self.total_fees += commission_cost
            self.entry_fee = commission_cost
            pnl_change -= commission_cost
            self.prev_price = price
            
            logger.debug(f"Short: {self.position_size:.4f} @ {price:.2f}")
        
        return pnl_change
    
    def _close_position(self, price: float) -> float:
        """Close current position"""
        if self.position == 0:
            return 0.0
        
        # Trade PnL for reporting (do NOT add to balance here, already mark-to-market'd step-by-step)
        if self.position == 1:
            trade_pnl = (price - self.entry_price) * self.position_size
        else:
            trade_pnl = (self.entry_price - price) * self.position_size
        
        position_value = self.position_size * price
        commission_cost = position_value * self.commission
        self.total_fees += commission_cost
        # Balance already includes trade_pnl via mark-to-market; only subtract exit fee now.
        self.balance -= commission_cost
        self.max_balance = max(self.max_balance, self.balance)
        net_pnl = trade_pnl - commission_cost - float(self.entry_fee)
        
        self.total_trades += 1
        if net_pnl > 0:
            self.winning_trades += 1
        
        self.trade_history.append({
            'step': self.current_step,
            'pnl': net_pnl,
            'return': net_pnl / (position_value if position_value > 0 else 1),
            'duration': self.current_trade_duration,
            'type': 'LONG' if self.position == 1 else 'SHORT',
            'hour': self.df.iloc[self.current_step]['open_time'].hour if 'open_time' in self.df.columns else (self.current_step % 24)
        })
        
        logger.debug(f"Close: PnL={net_pnl:.2f}, Balance={self.balance:.2f}")
        
        self.position = 0
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_fee = 0.0
        self.current_trade_duration = 0
        
        # For reward purposes, only return the exit fee impact.
        # (Trade PnL was already applied via mark-to-market each step.)
        return -commission_cost
    
    def render(self):
        """Render the environment"""
        print(f"Step: {self.current_step}, Balance: {self.balance:.2f}, Position: {self.position}")
    
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if len(self.balance_history) < 2:
            return {}
        
        returns = np.diff(self.balance_history) / self.balance_history[:-1]
        
        total_return = (self.balance - self.initial_balance) / self.initial_balance
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        max_drawdown = (self.max_balance - min(self.balance_history)) / self.max_balance
        
        wins = [t['pnl'] for t in self.trade_history if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.trade_history if t['pnl'] <= 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        durations = [t['duration'] for t in self.trade_history]
        avg_duration = np.mean(durations) if durations else 0
        
        # Hourly analysis (4-hour blocks)
        ui_blocks = []
        for i in range(0, 24, 4):
            block_trades = [t for t in self.trade_history if i <= t.get('hour', 0) < i+4]
            count = len(block_trades)
            win_count = len([t for t in block_trades if t['pnl'] > 0])
            rate = (win_count / count * 100) if count > 0 else 0
            ui_blocks.append({
                'hour': f"{i:02d}-{i+4:02d}",
                'trades': count,
                'winRate': round(rate, 1)
            })
        
        return {
            'total_return': round(total_return * 100, 2),
            'final_balance': round(self.balance, 2),
            'sharpe_ratio': round(sharpe_ratio * np.sqrt(252), 3),
            'max_drawdown': round(max_drawdown * 100, 2),
            'total_trades': self.total_trades,
            'win_rate': round(self.winning_trades / self.total_trades * 100, 2) if self.total_trades > 0 else 0,
            'wins': len(wins),
            'losses': len(losses),
            'avg_win_pnl': round(avg_win, 2),
            'avg_loss_pnl': round(avg_loss, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'avg_hold_time': f"{avg_duration:.1f} hours" if avg_duration > 0 else "0",
            'by_hour': ui_blocks,
            'total_fees': round(self.total_fees, 2)
        }
