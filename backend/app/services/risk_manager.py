"""
Risk Management System
"""
from loguru import logger
from datetime import datetime, timedelta
from typing import Optional


class RiskManager:
    """리스크 관리자"""
    
    def __init__(self):
        # 일일 제한
        self.daily_loss_limit = 500.0  # $500 손실 시 중지
        self.daily_trade_limit = 50  # 하루 최대 50 거래
        self.max_position_size = 0.1  # 잔고의 10%
        
        # 현재 상태
        self.today_pnl = 0.0
        self.today_trades = 0
        self.last_reset = datetime.now().date()
        self.is_halted = False
        
        # 포지션별 리스크
        self.default_stop_loss_percent = 2.0
        self.default_take_profit_percent = 5.0
        self.trailing_stop_enabled = False
        
    def check_daily_limits(self) -> tuple[bool, Optional[str]]:
        """일일 제한 확인"""
        self._reset_if_new_day()
        
        # 일일 손실 제한
        if self.today_pnl <= -self.daily_loss_limit:
            self.is_halted = True
            return False, f"Daily loss limit reached (${abs(self.today_pnl):.2f})"
        
        # 일일 거래 횟수 제한
        if self.today_trades >= self.daily_trade_limit:
            return False, f"Daily trade limit reached ({self.today_trades})"
        
        return True, None
    
    def validate_position_size(
        self,
        quantity: float,
        price: float,
        balance: float
    ) -> tuple[bool, Optional[str]]:
        """포지션 크기 검증"""
        position_value = quantity * price
        max_value = balance * self.max_position_size
        
        if position_value > max_value:
            suggested = max_value / price
            return False, f"Position too large. Max: {suggested:.4f}"
        
        return True, None
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        custom_percent: Optional[float] = None
    ) -> float:
        """스탑로스 가격 계산"""
        percent = custom_percent or self.default_stop_loss_percent
        
        if side == "BUY":
            return entry_price * (1 - percent / 100)
        else:  # SELL
            return entry_price * (1 + percent / 100)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        side: str,
        custom_percent: Optional[float] = None
    ) -> float:
        """익절 가격 계산"""
        percent = custom_percent or self.default_take_profit_percent
        
        if side == "BUY":
            return entry_price * (1 + percent / 100)
        else:  # SELL
            return entry_price * (1 - percent / 100)
    
    def should_close_position(
        self,
        current_price: float,
        entry_price: float,
        side: str,
        stop_loss: float,
        take_profit: float
    ) -> tuple[bool, Optional[str]]:
        """포지션 청산 여부 확인"""
        
        if side == "BUY":
            # 스탑로스
            if current_price <= stop_loss:
                return True, "STOP_LOSS"
            # 익절
            if current_price >= take_profit:
                return True, "TAKE_PROFIT"
        else:  # SELL
            # 스탑로스
            if current_price >= stop_loss:
                return True, "STOP_LOSS"
            # 익절
            if current_price <= take_profit:
                return True, "TAKE_PROFIT"
        
        return False, None
    
    def update_trailing_stop(
        self,
        current_price: float,
        entry_price: float,
        side: str,
        current_stop: float
    ) -> float:
        """트레일링 스탑 업데이트"""
        if not self.trailing_stop_enabled:
            return current_stop
        
        if side == "BUY":
            # 가격이 올라가면 스탑로스도 올림
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            if pnl_percent > 3:  # 3% 이상 수익
                new_stop = current_price * (1 - 0.015)  # 1.5% 아래로
                return max(new_stop, current_stop)
        else:  # SELL
            # 가격이 내려가면 스탑로스도 내림
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
            if pnl_percent > 3:
                new_stop = current_price * (1 + 0.015)
                return min(new_stop, current_stop)
        
        return current_stop
    
    def record_trade(self, pnl: float):
        """거래 기록"""
        self._reset_if_new_day()
        self.today_pnl += pnl
        self.today_trades += 1
        
        logger.info(f"Trade recorded: PnL=${pnl:.2f}, Today total: ${self.today_pnl:.2f}")
    
    def _reset_if_new_day(self):
        """날짜가 바뀌면 초기화"""
        today = datetime.now().date()
        if today > self.last_reset:
            logger.info("📅 New day, resetting risk manager")
            self.today_pnl = 0.0
            self.today_trades = 0
            self.is_halted = False
            self.last_reset = today
    
    def get_status(self) -> dict:
        """현재 상태 반환"""
        return {
            "is_halted": self.is_halted,
            "today_pnl": self.today_pnl,
            "today_trades": self.today_trades,
            "daily_loss_limit": self.daily_loss_limit,
            "daily_trade_limit": self.daily_trade_limit,
            "remaining_trades": max(0, self.daily_trade_limit - self.today_trades),
            "remaining_loss": max(0, self.daily_loss_limit + self.today_pnl)
        }
    
    def update_settings(
        self,
        daily_loss_limit: Optional[float] = None,
        daily_trade_limit: Optional[int] = None,
        max_position_size: Optional[float] = None,
        stop_loss_percent: Optional[float] = None,
        take_profit_percent: Optional[float] = None,
        trailing_stop: Optional[bool] = None
    ):
        """설정 업데이트"""
        if daily_loss_limit is not None:
            self.daily_loss_limit = daily_loss_limit
        if daily_trade_limit is not None:
            self.daily_trade_limit = daily_trade_limit
        if max_position_size is not None:
            self.max_position_size = max_position_size
        if stop_loss_percent is not None:
            self.default_stop_loss_percent = stop_loss_percent
        if take_profit_percent is not None:
            self.default_take_profit_percent = take_profit_percent
        if trailing_stop is not None:
            self.trailing_stop_enabled = trailing_stop
        
        logger.info("Risk management settings updated")


# Global instance
risk_manager = RiskManager()
