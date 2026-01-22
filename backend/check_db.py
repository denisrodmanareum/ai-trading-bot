import sqlite3
import datetime

conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()

try:
    cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 5")
    rows = cursor.fetchall()
    if not rows:
        print("No trades found in DB.")
    else:
        print("Recent Trades:")
        for row in rows:
            print(row)
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
