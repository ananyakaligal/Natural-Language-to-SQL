import sqlite3

# Convert .sql file to .db
with open("Chinook_PostgreSql.sql", "r") as f:
    sql_script = f.read()

conn = sqlite3.connect("chinook.db")
cursor = conn.cursor()
cursor.executescript(sql_script)
conn.commit()
conn.close()
print("✅ chinook.db created successfully.")
