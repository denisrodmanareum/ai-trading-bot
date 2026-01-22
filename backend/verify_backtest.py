import asyncio
import os
import sys

# Add backend dir to path so imports work
sys.path.append(os.getcwd())

from ai.trainer import backtest_agent
from app.core.config import settings

async def verify_backtest():
    print("Verifying backtest functionality...")
    try:
        # 1. Check models
        model_dir = "data/models" # Relative to backend root
        if not os.path.exists(model_dir):
            print(f"Error: {model_dir} does not exist")
            return

        models = [f for f in os.listdir(model_dir) if f.endswith('.zip')]
        print(f"Found models: {models}")
        
        if not models:
            print("No models found to test.")
            return

        # 2. Run Backtest
        print("Running backtest_agent (default params)...")
        # backtest_agent uses default hardcoded 30 days if not flexible
        results = await backtest_agent(
            symbol="BTCUSDT"
        )
        print("Backtest Results:", results)
        
    except Exception as e:
        print(f"Backtest Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_backtest())
