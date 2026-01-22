import asyncio
from app.database import engine, Base
import app.models  # Register models

async def main():
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Optional: Wipe clean to be sure
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully.")
    
    # Verify tables
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: sync_conn.dialect.get_table_names(sync_conn))
        print(f"Tables created: {tables}")

if __name__ == "__main__":
    asyncio.run(main())
