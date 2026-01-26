import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.deep_models.train_lstm import train_lstm

async def main():
    print("Starting LSTM training for 15m...")
    try:
        # Train for 15m interval, 45 days
        await train_lstm(
            symbol="BTCUSDT",
            interval="15m",
            days=45,
            epochs=50,
            batch_size=32
        )
        print("Training complete!")
    except Exception as e:
        print(f"Training failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
