import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.database import init_db

async def run():
    print("Starting database initialization...")
    await init_db()
    print("Initialization complete!")

if __name__ == "__main__":
    asyncio.run(run())
