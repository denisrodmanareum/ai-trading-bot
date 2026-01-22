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
    days: int = 90
) -> pd.DataFrame:
    """Fetch historical data for training"""
    logger.info(f"Fetching {days} days of {interval} data for {symbol}")
    
    client = BinanceClient()
    await client.initialize()
    
    try:
        # Calculate number of candles needed
        candles_per_day = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1
        }
        
        limit = candles_per_day.get(interval, 24) * days
        limit = min(limit, 1000)  # Binance limit
        
        df = await client.get_klines(symbol, interval, limit)
        
        # Add technical indicators
        df = add_technical_indicators(df)
        
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
    logger.info(f"Starting training for {episodes} episodes...")
    
    try:
        # Fetch training data
        df = await fetch_training_data(symbol, interval, days)
        
        # Calculate actual timesteps based on data length
        # 1 Episode = 1 full pass through the data
        total_timesteps = episodes * len(df)
        logger.info(f"Data length: {len(df)} candles. Total timesteps: {total_timesteps}")
        
        # Create agent
        agent = TradingAgent()
        
        # Train
        model_path = agent.train(
            df=df,
            total_timesteps=total_timesteps,
            save_freq=save_freq,
            reward_strategy=reward_strategy,
            leverage=leverage,
            symbol=symbol
        )
        
        # Enforce limit one last time
        try:
            from cleanup_models import cleanup_models
            cleanup_models()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        logger.info(f"Training completed! Model saved to {model_path}")
        return model_path
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


async def backtest_agent(
    model_path: str = None,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    start_date: str = None,
    end_date: str = None,
    initial_balance: float = 10000.0,
    days: int = 30
):
    """Backtest trained agent"""
    logger.info(f"Starting backtest with ${initial_balance} for {days} days...")
    
    try:
        # Fetch test data
        df = await fetch_training_data(symbol, interval, days=days)
        
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
        results = agent.backtest(df, initial_balance=initial_balance)
        
        logger.info(f"Backtest completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise


if __name__ == "__main__":
    # Example: Train agent
    asyncio.run(train_agent(episodes=100))
