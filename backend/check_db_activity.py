import sqlite3
import pandas as pd
from datetime import datetime

conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()

print("--- Database Check ---")

# Check Candles
cursor.execute("SELECT COUNT(*) FROM candles")
candle_count = cursor.fetchone()[0]
print(f"Total Candles: {candle_count}")

if candle_count > 0:
    cursor.execute("SELECT symbol, interval, timestamp, close FROM candles ORDER BY timestamp DESC LIMIT 5")
    print("\nLatest Candles:")
    for row in cursor.fetchall():
        print(row)

# Check Trades
cursor.execute("SELECT COUNT(*) FROM trades")
trade_count = cursor.fetchone()[0]
print(f"\nTotal Trades: {trade_count}")

if trade_count > 0:
    cursor.execute("SELECT symbol, action, side, price, timestamp FROM trades ORDER BY timestamp DESC LIMIT 5")
    print("\nLatest Trades:")
    for row in cursor.fetchall():
        print(row)

conn.close()
