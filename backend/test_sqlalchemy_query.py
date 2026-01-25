
import asyncio
from app.database import SessionLocal
from app.models import Trade
from sqlalchemy import select

async def test_mapping():
    print("Testing SQLAlchemy mapping...")
    try:
        async with SessionLocal() as session:
            query = select(Trade).limit(1)
            result = await session.execute(query)
            trade = result.scalar()
            print("Query executed successfully.")
            if trade:
                print(f"Fetched trade: {trade.id}, roi={trade.roi}")
            else:
                print("No trades found, but query worked.")
    except Exception as e:
        print(f"Query Failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_mapping())
