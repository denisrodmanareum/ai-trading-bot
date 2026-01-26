import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.deep_models.train_lstm import train_lstm

async def main():
    print("Starting DEBUG LSTM training for 15m...")
    try:
        # Mini training for debug
        await train_lstm(
            symbol="BTCUSDT",
            interval="15m",
            days=2,
            epochs=1,
            batch_size=32
        )
        print("DEBUG Training complete!")
    except Exception as e:
        print(f"DEBUG Training failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
