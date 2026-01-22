import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Trade
from sqlalchemy import select
from datetime import datetime, date

async def check_trades():
    async with SessionLocal() as session:
        query = select(Trade).order_by(Trade.timestamp.desc()).limit(10)
        result = await session.execute(query)
        trades = result.scalars().all()
        
        print(f"\n--- Latest 10 Trades ---")
        if not trades:
            print("No trades found in database.")
        for t in trades:
            print(f"ID: {t.id} | {t.timestamp} | {t.symbol} | {t.action} | PnL: {t.pnl}")
            
        today = date.today()
        print(f"\nSystem Today: {today}")
        print(f"Now UTC: {datetime.utcnow()}")
        print(f"Now Local: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(check_trades())
