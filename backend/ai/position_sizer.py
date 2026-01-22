"""
Dynamic Position Sizing using Kelly Criterion
Adjusts position size based on historical win rate and risk/reward
"""
import numpy as np
from typing import Dict, List
from loguru import logger


class PositionSizer:
    """
    Kelly Criterion-based position sizing
    Formula: Kelly% = (Win% * Avg Win - Loss% * Avg Loss) / Avg Win
    
    Uses Fractional Kelly (25%) for risk management
    """
    
    def __init__(
        self,
        kelly_fraction: float = 0.25,
        min_position_pct: float = 0.01,
        max_position_pct: float = 0.10,
        min_trades_for_kelly: int = 10
    ):
        self.kelly_fraction = kelly_fraction
        self.min_position_pct = min_position_pct
        self.max_position_pct = max_position_pct
        self.min_trades_for_kelly = min_trades_for_kelly
        
        # Trade history
        self.trade_history: List[Dict] = []
        
    def add_trade_result(self, pnl: float, is_win: bool):
        """
        Record trade result for Kelly calculation
        """
        self.trade_history.append({
            'pnl': pnl,
            'is_win': is_win
        })
        
        # Keep last 100 trades
        if len(self.trade_history) > 100:
            self.trade_history.pop(0)
    
    def calculate_position_size(
        self,
        balance: float,
        current_price: float,
        confidence: float = 1.0
    ) -> Dict:
        """
        Calculate optimal position size
        
        Args:
            balance: Current account balance
            current_price: Current asset price
            confidence: AI confidence (0-1), scales Kelly%
            
        Returns:
            {
                'position_size': float (in base asset),
                'position_value': float (in USD),
                'position_pct': float (% of balance),
                'method': str
            }
        """
        try:
            # Not enough trade history, use conservative default
            if len(self.trade_history) < self.min_trades_for_kelly:
                position_pct = self.min_position_pct
                method = "conservative_default"
            else:
                # Calculate Kelly Criterion
                kelly_pct = self._calculate_kelly()
                
                # Apply fraction and confidence
                position_pct = kelly_pct * self.kelly_fraction * confidence
                method = "kelly_criterion"
            
            # Apply limits
            position_pct = np.clip(position_pct, self.min_position_pct, self.max_position_pct)
            
            # Calculate position size
            position_value = balance * position_pct
            position_size = position_value / current_price if current_price > 0 else 0
            
            result = {
                'position_size': round(position_size, 6),
                'position_value': round(position_value, 2),
                'position_pct': round(position_pct * 100, 2),
                'method': method
            }
            
            logger.debug(f"Position Size: {result['position_size']} ({result['position_pct']}% of balance)")
            return result
            
        except Exception as e:
            logger.error(f"Position sizing failed: {e}")
            # Fallback to minimum
            position_value = balance * self.min_position_pct
            position_size = position_value / current_price if current_price > 0 else 0
            
            return {
                'position_size': round(position_size, 6),
                'position_value': round(position_value, 2),
                'position_pct': self.min_position_pct * 100,
                'method': 'fallback'
            }
    
    def _calculate_kelly(self) -> float:
        """
        Calculate Kelly Criterion percentage
        
        Kelly% = (p * W - (1-p) * L) / W
        where:
            p = win rate
            W = average win
            L = average loss
        """
        wins = [t['pnl'] for t in self.trade_history if t['is_win']]
        losses = [abs(t['pnl']) for t in self.trade_history if not t['is_win']]
        
        if not wins or not losses:
            return self.min_position_pct  # Not enough data
        
        win_rate = len(wins) / len(self.trade_history)
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)
        
        # Kelly formula
        if avg_win > 0:
            kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        else:
            kelly_pct = 0
        
        # Kelly can be negative (don't trade) or > 1 (aggressive)
        # We clip to reasonable range
        kelly_pct = np.clip(kelly_pct, 0, 0.5)  # Max 50% of balance
        
        return kelly_pct
    
    def get_statistics(self) -> Dict:
        """
        Get current trading statistics
        """
        if len(self.trade_history) < self.min_trades_for_kelly:
            return {
                'total_trades': len(self.trade_history),
                'status': 'insufficient_data',
                'min_required': self.min_trades_for_kelly
            }
        
        wins = [t for t in self.trade_history if t['is_win']]
        losses = [t for t in self.trade_history if not t['is_win']]
        
        win_rate = len(wins) / len(self.trade_history) if self.trade_history else 0
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t['pnl']) for t in losses]) if losses else 0
        
        profit_factor = (len(wins) * avg_win) / (len(losses) * avg_loss) if losses and avg_loss > 0 else 0
        
        return {
            'total_trades': len(self.trade_history),
            'win_rate': round(win_rate * 100, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'kelly_pct': round(self._calculate_kelly() * 100, 2),
            'recommended_position_pct': round(self._calculate_kelly() * self.kelly_fraction * 100, 2)
        }
    
    def reset(self):
        """Reset trade history"""
        self.trade_history = []
