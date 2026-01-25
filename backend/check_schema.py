
import sqlite3

db_path = "e:/auto/ai-trading-bot/backend/trading_bot.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(trades)")
    columns = cursor.fetchall()
    print("Columns in trades table:")
    for col in columns:
        print(col)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
