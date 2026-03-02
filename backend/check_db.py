import sqlite3

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(biometric_templates)')
print('Biometric columns:', cursor.fetchall())

cursor.execute('SELECT COUNT(*) FROM biometric_templates')
print('Total records:', cursor.fetchone())

cursor.execute('SELECT * FROM biometric_templates LIMIT 1')
row = cursor.fetchone()
if row:
    for i, val in enumerate(row):
        print(f'Col {i}: type={type(val).__name__}, preview={str(val)[:100]}')

conn.close()
