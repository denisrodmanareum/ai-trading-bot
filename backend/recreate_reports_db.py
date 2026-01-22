import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.database import engine, Base
from app.models import DailyReport

async def recreate():
    print("Recreating daily_reports table...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[DailyReport.__table__])
        await conn.run_sync(Base.metadata.create_all, tables=[DailyReport.__table__])
    print("Recreation complete!")

if __name__ == "__main__":
    asyncio.run(recreate())
