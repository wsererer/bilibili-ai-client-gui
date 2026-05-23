import sqlite3
conn = sqlite3.connect('data/bilibili_client.db')
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', tables)
for t in tables:
    print(f'\nTable {t[0]}:')
    rows = cur.execute(f"SELECT * FROM {t[0]} LIMIT 10").fetchall()
    print(rows)