import asyncio
import os
import sys

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading.binance_client import BinanceClient
from app.database import init_db

async def test_connections():
    print("[DEBUG] Starting connection test...")
    
    # 1. Test DB
    try:
        print("[DEBUG] Testing Database Init...")
        await init_db()
        print("[DEBUG] Database Init: OK")
    except Exception as e:
        print(f"[DEBUG] Database Init FAILED: {e}")
        return

    # 2. Test Binance
    try:
        print("[DEBUG] Testing Binance Client Init...")
        client = BinanceClient()
        await client.initialize()
        print("[DEBUG] Binance Client Init: OK")
        
        # Test basic fetch
        print("[DEBUG] Fetching Server Time...")
        time = await client.client.get_server_time()
        print(f"[DEBUG] Server Time: {time}")
        
        await client.close()
        print("[DEBUG] Binance Client Closed: OK")
        
    except Exception as e:
        print(f"[DEBUG] Binance Init FAILED: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_connections())
