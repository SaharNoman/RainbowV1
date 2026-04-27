import sqlite3

conn = sqlite3.connect('inventory.db')
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS sales')
conn.commit()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables after drop:', cur.fetchall())

conn.close()
print('Done - now run: python import_sales.py')