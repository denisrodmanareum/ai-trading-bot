from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from app.database import Base
from datetime import datetime

class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    interval = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    # Technical Indicators (Optional - can be NULL if raw only)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    signal = Column(Float, nullable=True)
    bb_upper = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String) # LONG, SHORT, CLOSE
    side = Column(String)   # BUY, SELL
    price = Column(Float)
    quantity = Column(Float)
    
    # Results
    pnl = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    
    # Context
    strategy = Column(String, default="ai_ppo") # ai_ppo, manual, etc
    reason = Column(String, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

class TradeState(Base):
    __tablename__ = "trade_states"
    
    symbol = Column(String, primary_key=True, index=True)
    data = Column(String) # JSON string of the brackets dict
    updated_at = Column(DateTime, default=datetime.utcnow)
    
class ModelMeta(Base):
    __tablename__ = "model_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True)
    filename = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metrics
    training_episodes = Column(Integer)
    avg_reward = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False)

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True) # Report for which day
    total_trades = Column(Integer)
    wins = Column(Integer)
    losses = Column(Integer)
    win_rate = Column(Float)
    total_pnl = Column(Float)
    total_commission = Column(Float, default=0.0)
    ai_remark = Column(String)
    retrained = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
