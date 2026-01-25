"""
Manual migration script to add new columns to trades table
"""
import sqlite3
from loguru import logger

def migrate():
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    try:
        # Add roi column
        cursor.execute("ALTER TABLE trades ADD COLUMN roi FLOAT NULL")
        logger.info("Added 'roi' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("'roi' column already exists")
        else:
            raise
    
    try:
        # Add entry_time column
        cursor.execute("ALTER TABLE trades ADD COLUMN entry_time DATETIME NULL")
        logger.info("Added 'entry_time' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("'entry_time' column already exists")
        else:
            raise
    
    try:
        # Add exit_time column
        cursor.execute("ALTER TABLE trades ADD COLUMN exit_time DATETIME NULL")
        logger.info("Added 'exit_time' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("'exit_time' column already exists")
        else:
            raise
    
    try:
        # Add status column with default
        cursor.execute("ALTER TABLE trades ADD COLUMN status VARCHAR DEFAULT 'CLOSED'")
        logger.info("Added 'status' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("'status' column already exists")
        else:
            raise
    
    conn.commit()
    
    # Verify
    cursor.execute('PRAGMA table_info(trades)')
    columns = [row[1] for row in cursor.fetchall()]
    
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print("\nTrades table columns:")
    for col in columns:
        print(f"  - {col}")
    print("\n" + "="*60)
    
    # Check for new columns
    new_cols = ['roi', 'entry_time', 'exit_time', 'status']
    missing = [col for col in new_cols if col not in columns]
    
    if missing:
        print(f"\nWARNING: Missing columns: {missing}")
    else:
        print("\nSUCCESS: All new columns added!")
    
    conn.close()

if __name__ == "__main__":
    migrate()
