import sqlite3

with sqlite3.connect('data/nexus.db') as conn:
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS nexus_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT,
        source TEXT,
        status TEXT DEFAULT 'pending',
        result TEXT,
        context TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    try:
        cur.execute("ALTER TABLE nexus_commands ADD COLUMN result TEXT")
    except Exception:
        pass
    conn.commit()
    print('nexus_commands ready in local DB')
