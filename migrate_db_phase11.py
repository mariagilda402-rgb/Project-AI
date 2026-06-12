import sqlite3

# Update local DB schema
db_path = 'data/nexus.db'
with sqlite3.connect(db_path) as conn:
    cur = conn.cursor()
    
    # Add ai_analysis column to journal_entries if not exists
    try:
        cur.execute("ALTER TABLE journal_entries ADD COLUMN ai_analysis TEXT")
        print("Added ai_analysis to journal_entries")
    except Exception as e:
        print(f"journal_entries ai_analysis: {e}")
    
    # Add device_source column to journal_entries if not exists
    try:
        cur.execute("ALTER TABLE journal_entries ADD COLUMN device_source TEXT DEFAULT 'pc'")
        print("Added device_source to journal_entries")
    except Exception as e:
        print(f"journal_entries device_source: {e}")

    # Create mobile_gps_log if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mobile_gps_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lon REAL,
            accuracy REAL,
            recorded_at TEXT
        )
    """)
    print("Created mobile_gps_log table")

    # Add result column to nexus_commands if not exists
    try:
        cur.execute("ALTER TABLE nexus_commands ADD COLUMN result TEXT")
        print("Added result to nexus_commands")
    except Exception as e:
        print(f"nexus_commands result: {e}")

    conn.commit()
    print("DB migration complete!")
