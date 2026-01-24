"""
AI Training Module
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

from ai.agent import TradingAgent
from ai.features import add_technical_indicators
from trading.binance_client import BinanceClient
from app.core.config import settings


async def fetch_training_data(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 90,
    warmup_candles: int = 200 # Needed for indicators like EMA 200
) -> pd.DataFrame:
    """Fetch historical data for training/backtesting"""
    logger.info(f"Fetching {days} days of {interval} data for {symbol} (+{warmup_candles} warmup)")
    
    client = BinanceClient()
    await client.initialize()
    
    try:
        # Calculate total number of candles needed
        candles_per_day = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1
        }
        
        total_needed = (candles_per_day.get(interval, 24) * days) + warmup_candles
        
        # Binance limit is 1500 per request. We need to fetch in chunks if total_needed > 1500
        all_klines = []
        last_timestamp = None
        
        while len(all_klines) < total_needed:
            limit = min(1500, total_needed - len(all_klines))
            
            # If we have a last_timestamp, we fetch BEFORE it (since we want the latest 'days' and then warmup)
            # Actually klines fetching is usually "startTime" to "endTime" or "limit". 
            # futures_klines(symbol=..., interval=..., limit=...) returns the LATEST 'limit' candles if no startTime.
            # So if we want 10,000 candles, we can fetch 1500, then fetch the next 1500 using endTime=first_timestamp_of_prev_batch-1
            
            end_time = last_timestamp - 1 if last_timestamp else None
            
            klines = await client.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                endTime=end_time
            )
            
            if not klines:
                break
                
            # klines are in chronological order: [oldest, ..., newest]
            all_klines = klines + all_klines # Prepend older klines
            last_timestamp = klines[0][0] # Oldest timestamp in this batch
            
            if len(klines) < limit:
                break
        
        # Convert to DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Basic cleanup
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        # Add technical indicators
        df = add_technical_indicators(df)
        
        # The first few rows might still have NaNs due to windowing if warmup wasn't enough,
        # but add_technical_indicators already does bfill().ffill().
        
        logger.info(f"Fetched {len(df)} candles with indicators")
        return df
        
    finally:
        await client.close()


async def train_agent(
    episodes: int = 1000,
    save_freq: int = 100,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 90,
    leverage: int = 5,
    reward_strategy: str = "simple"
):
    """Train the trading agent"""
    logger.info(f"🎯 Starting training for {symbol} ({interval}) - {episodes} episodes...")
    
    try:
        # Fetch training data
        df = await fetch_training_data(symbol, interval, days)
        
        # Calculate actual timesteps based on data length
        # 1 Episode = 1 full pass through the data
        total_timesteps = episodes * len(df)
        logger.info(f"📊 Data length: {len(df)} candles. Total timesteps: {total_timesteps}")
        
        # Create agent
        agent = TradingAgent()
        
        # Train (interval 파라미터 추가)
        model_path = agent.train(
            df=df,
            total_timesteps=total_timesteps,
            save_freq=save_freq,
            reward_strategy=reward_strategy,
            leverage=leverage,
            symbol=symbol,
            interval=interval  # ✅ interval 전달
        )
        
        logger.info(f"✅ Training completed! Model saved to {model_path}")
        logger.info(f"📁 Model name: ppo_{symbol}_{interval}_YYYYMMDD_HHMM.zip")
        return model_path
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise


async def backtest_agent(
    model_path: str = None,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    start_date: str = None,
    end_date: str = None,
    initial_balance: float = 10000.0,
    days: int = 30,
    warmup_candles: int = 300 # Increased for stability
):
    """Backtest trained agent"""
    logger.info(f"Starting backtest with ${initial_balance} for {days} days at {interval}...")
    
    try:
        # Fetch test data with warmup
        df = await fetch_training_data(symbol, interval, days=days, warmup_candles=warmup_candles)
        
        # Load agent
        agent = TradingAgent()
        if model_path:
            agent.load_model(model_path)
        else:
            # Load latest model
            import os
            model_dir = settings.AI_MODEL_PATH
            models = [f for f in os.listdir(model_dir) if f.endswith('.zip')]
            if not models:
                raise ValueError("No trained models found")
            latest_model = os.path.join(model_dir, sorted(models)[-1])
            agent.load_model(latest_model)
        
        # Run backtest
        # We should pass the data WITHOUT warmup period to the backtest environment
        # but the indicators are already calculated on the full set.
        # environment.py starts from 0. We should probably slice the DF to only include
        # the requested period for the actual trading steps, but keeping history for indicators.
        
        # Slicing: keep only the last 'total_steps' candles for trading, 
        # but they already HAVE indicator values calculated using the warmup candles.
        total_steps = len(df) - warmup_candles
        if total_steps > 0:
            # We want to trade on the last 'total_steps'
            # But TradingEnvironment just goes through the DF.
            # If we pass the full DF, it trades for days + warmup.
            # Let's slice it.
            df_test = df.iloc[warmup_candles:].reset_index(drop=True)
            results = agent.backtest(df_test, initial_balance=initial_balance)
        else:
            results = agent.backtest(df, initial_balance=initial_balance)
        
        logger.info(f"Backtest completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise


if __name__ == "__main__":
    # Example: Train agent
    asyncio.run(train_agent(episodes=100))
