import numpy as np

class BaseReward:
    def __init__(self):
        self.rewards_history = []
        
    def reset(self):
        self.rewards_history = []
        
    def calculate(self, action, pnl, position_size, balance, current_price=0):
        raise NotImplementedError

class PnLReward(BaseReward):
    """Simple PnL Reward"""
    def calculate(self, action, pnl, position_size, balance, current_price=0):
        return pnl

class SharpeReward(BaseReward):
    """
    Reward based on Sharpe Ratio (Risk-Adjusted Return).
    Penalizes volatility.
    """
    def __init__(self, window_size=50):
        super().__init__()
        self.window_size = window_size
        self.returns_history = []
        
    def reset(self):
        self.returns_history = []

    def calculate(self, action, pnl, position_size, balance, current_price=0):
        # Calculate approximate return based on balance change
        if balance == 0:
            ret = 0
        else:
             # Ret = PnL / Previous Balance? 
             # Or just PnL / Balance? 
             # Let's use PnL / Balance approx.
             ret = pnl / balance
            
        self.returns_history.append(ret)
        
        if len(self.returns_history) < 2:
            return ret
            
        # Keep window
        if len(self.returns_history) > self.window_size:
            self.returns_history.pop(0)
            
        returns_np = np.array(self.returns_history)
        std = np.std(returns_np)
        
        if std == 0:
            return ret
            
        # Sharpe Step
        sharpe_step = ret / (std + 1e-6)
        return sharpe_step

class SortinoReward(BaseReward):
    """
    Sortino Ratio: Penalizes only downside volatility.
    """
    def __init__(self, window_size=50):
        super().__init__()
        self.window_size = window_size
        self.returns_history = []
        
    def reset(self):
        self.returns_history = []

    def calculate(self, action, pnl, position_size, balance, current_price=0):
        if balance == 0:
            ret = 0
        else:
            ret = pnl / balance
            
        self.returns_history.append(ret)
        
        if len(self.returns_history) < 2:
            return ret
            
        if len(self.returns_history) > self.window_size:
            self.returns_history.pop(0)
            
        returns_np = np.array(self.returns_history)
        
        # Downside deviation only
        downside_returns = returns_np[returns_np < 0]
        
        if len(downside_returns) == 0:
            downside_std = 1e-6
        else:
            downside_std = np.std(downside_returns) + 1e-6
            
        sortino_step = ret / downside_std
        return sortino_step


class ImprovedReward(BaseReward):
    """
    Multi-Factor Reward System
    - PnL (40%)
    - Risk-Adjusted Return (30%)
    - Trade Cost (10%)
    - Drawdown Penalty (15%)
    - Trade Frequency Control (5%)
    """
    def __init__(self, window_size=50, fee_rate=0.0004):
        super().__init__()
        self.window_size = window_size
        self.fee_rate = fee_rate
        self.returns_history = []
        self.balance_history = []
        self.trade_count = 0
        self.episode_trades = 0
        
    def reset(self):
        self.returns_history = []
        self.balance_history = []
        self.trade_count = 0
        self.episode_trades = 0
        
    def calculate(self, action, pnl, position_size, balance, current_price=0):
        # 1. PnL Reward (normalized by balance)
        if balance == 0 or balance < 1:
            pnl_reward = 0
        else:
            pnl_reward = pnl / balance
        
        # 2. Risk-Adjusted Return (Sharpe-like)
        self.returns_history.append(pnl_reward)
        if len(self.returns_history) > self.window_size:
            self.returns_history.pop(0)
            
        if len(self.returns_history) >= 5:
            returns_np = np.array(self.returns_history)
            mean_return = np.mean(returns_np)
            std_return = np.std(returns_np)
            
            if std_return > 1e-6:
                risk_adjusted = mean_return / std_return
            else:
                risk_adjusted = mean_return
        else:
            risk_adjusted = pnl_reward
        
        # 3. Trade Cost Penalty
        if action in [1, 2]:  # Entry (LONG or SHORT)
            trade_cost = -self.fee_rate  # Negative reward for fees
            self.trade_count += 1
            self.episode_trades += 1
        else:
            trade_cost = 0
        
        # 4. Drawdown Penalty
        self.balance_history.append(balance)
        if len(self.balance_history) > self.window_size:
            self.balance_history.pop(0)
            
        if len(self.balance_history) >= 2:
            peak = max(self.balance_history)
            if peak > 0:
                current_drawdown = (peak - balance) / peak
                drawdown_penalty = -current_drawdown * 0.5  # Penalize drawdowns
            else:
                drawdown_penalty = 0
        else:
            drawdown_penalty = 0
        
        # 5. Excessive Trading Penalty (prevent overtrading)
        if self.episode_trades > 100:
            freq_penalty = -0.01 * (self.episode_trades - 100) / 100
        else:
            freq_penalty = 0
        
        # 6. Holding Reward (encourage patience)
        if action == 0 and position_size > 0:  # Holding position
            holding_reward = 0.0001  # Small positive reward
        else:
            holding_reward = 0
        
        # Combined Reward with weights (🔧 공격적 수익 추구형으로 리밸런싱)
        total_reward = (
            0.45 * pnl_reward +           # PnL 45% (🔧 35→45)
            0.20 * risk_adjusted +        # Risk-adjusted 20% (🔧 30→20)
            0.10 * trade_cost +           # Trade cost 10%
            0.15 * drawdown_penalty +     # Drawdown 15%
            0.05 * freq_penalty +         # Frequency 5%
            0.05 * holding_reward         # Holding 5%
        )
        
        # Clip to prevent extreme values
        total_reward = np.clip(total_reward, -10, 10)
        
        return total_reward


def get_reward_strategy(strategy_name: str = "simple") -> BaseReward:
    """Factory function to get reward strategy instance"""
    strategies = {
        "simple": PnLReward,
        "sharpe": SharpeReward,
        "sortino": SortinoReward,
        "improved": ImprovedReward
    }
    
    reward_class = strategies.get(strategy_name.lower(), PnLReward)
    return reward_class()
