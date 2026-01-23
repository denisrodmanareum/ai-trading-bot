import asyncio
import pandas as pd
import numpy as np
from ai.agent import TradingAgent
from ai.trainer import fetch_training_data
from loguru import logger
import os
from app.core.config import settings

async def diagnose_agent():
    symbol = "BTCUSDT"
    interval = "1h"
    days = 5
    
    logger.info("Fetching diagnostic data...")
    df = await fetch_training_data(symbol, interval, days=days)
    
    agent = TradingAgent()
    # Load the latest model
    model_dir = settings.AI_MODEL_PATH
    models = [f for f in os.listdir(model_dir) if f.endswith('.zip')]
    if not models:
        logger.error("No models found!")
        return
    
    latest_model = os.path.join(model_dir, sorted(models)[-1])
    logger.info(f"Loading model: {latest_model}")
    agent.load_model(latest_model)
    
    # Create environment
    env = agent.create_environment(df)
    obs, _ = env.reset()
    
    logger.info(f"Observation shape: {obs.shape}")
    
    # Test a few steps
    for i in range(10):
        action, _states = agent.model.predict(obs, deterministic=True)
        
        # Log observation details for the first step
        if i == 0:
            logger.info("Sample Observation Values:")
            features = [
                "close", "volume", "rsi", "macd", "signal", "bb_upper", "bb_lower", "atr",
                "position", "position_size", "entry_price", "unrealized_pnl"
            ]
            if len(obs) > 12:
                features += ["stoch_k_fast", "stoch_d_fast", "stoch_k_mid", "stoch_d_mid", "stoch_k_slow", "stoch_d_slow"]
            
            for name, val in zip(features, obs):
                logger.info(f"  {name}: {val}")
        
        obs, reward, done, truncated, info = env.step(action)
        logger.info(f"Step {i}: Action={action}, Reward={reward:.4f}, Position={info['position']}")
        
        if done or truncated:
            break

if __name__ == "__main__":
    asyncio.run(diagnose_agent())
