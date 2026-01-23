"""
Trade History Database Models
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Trade(Base):
    """거래 기록"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    leverage = Column(Integer, default=1)
    
    # PnL
    pnl = Column(Float)
    pnl_percent = Column(Float)
    
    # Status
    status = Column(String(20), default='OPEN')  # OPEN, CLOSED, LIQUIDATED
    is_win = Column(Boolean)
    
    # Strategy
    strategy = Column(String(50))  # MANUAL, AI_AUTO
    ai_confidence = Column(Float)  # AI 신뢰도 (0-1)
    
    # Exit info
    exit_reason = Column(String(50))  # TAKE_PROFIT, STOP_LOSS, MANUAL, LIQUIDATION
    exit_timestamp = Column(DateTime)
    
    # Risk metrics
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(Float)


class DailyStats(Base):
    """일일 통계"""
    __tablename__ = 'daily_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True)
    
    # Trading stats
    total_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    
    # PnL
    total_pnl = Column(Float, default=0)
    total_pnl_percent = Column(Float, default=0)
    
    # Balance
    starting_balance = Column(Float)
    ending_balance = Column(Float)
    
    # AI performance
    ai_trades = Column(Integer, default=0)
    ai_win_rate = Column(Float, default=0)
    manual_trades = Column(Integer, default=0)
    manual_win_rate = Column(Float, default=0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0)
    sharpe_ratio = Column(Float)
    
    # Best/Worst
    best_trade_pnl = Column(Float)
    worst_trade_pnl = Column(Float)
