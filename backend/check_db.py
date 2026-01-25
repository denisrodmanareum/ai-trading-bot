import sqlite3

conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(trades)')

print('\nTrades Table Structure:')
print('-' * 50)
for row in cursor.fetchall():
    nullable = "NULL" if row[3] == 0 else "NOT NULL"
    print(f'  {row[1]:20s} {row[2]:15s} {nullable:10s}')

conn.close()
print('-' * 50)
print('Check complete!')
