import sqlite3, os, sys
db_path = os.path.join('C:/D drive/New Python Journey geezzzz/INConvo/backend', 'awaazai.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM voice')
print('Voice count:', cur.fetchone()[0])
cur.execute('SELECT id, provider, tier FROM voice LIMIT 20')
for row in cur.fetchall():
    print(row)
