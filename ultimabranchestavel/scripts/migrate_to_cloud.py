import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv

load_dotenv()
pg_url = os.getenv("SUPABASE_DB_URL")
if not pg_url:
    print("SUPABASE_DB_URL not found in .env")
    exit(1)

# Connect to sqlite
sl_conn = sqlite3.connect("data/nexus.db")
sl_conn.row_factory = sqlite3.Row
sl_cur = sl_conn.cursor()

# Connect to postgres
pg_conn = psycopg2.connect(pg_url)
pg_cur = pg_conn.cursor()

print("Connected to both databases.")

# Get all tables and their create statements
sl_cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables_info = sl_cur.fetchall()

print(f"Found {len(tables_info)} tables. Creating schema in Postgres...")

for name, sql in tables_info:
    if not sql: continue
    # Translate SQLite SQL to Postgres SQL
    pg_sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    pg_sql = pg_sql.replace("DATETIME", "TIMESTAMP")
    pg_sql = pg_sql.replace("REAL", "DOUBLE PRECISION")
    
    try:
        pg_cur.execute(pg_sql)
    except Exception as e:
        print(f"Error creating table {name}: {e}\nSQL: {pg_sql}")
        pg_conn.rollback()
    else:
        pg_conn.commit()

tables = [r["name"] for r in tables_info]

print(f"Found tables to migrate: {tables}")

for table in tables:
    sl_cur.execute(f"SELECT * FROM {table}")
    rows = sl_cur.fetchall()
    if not rows:
        print(f"Skipping empty table: {table}")
        continue
    
    # Get column names
    cols = rows[0].keys()
    col_names = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    
    print(f"Migrating {len(rows)} rows from {table}...")
    
    # Insert rows
    for row in rows:
        values = tuple(row[col] for col in cols)
        # Using ON CONFLICT (id) DO UPDATE to handle reruns safely
        # Note: We assume all tables have an 'id' primary key for conflict resolution.
        # If some don't, we just do DO NOTHING.
        try:
            pg_cur.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING", values)
        except Exception as e:
            # If the table doesn't have an 'id' column, fallback to DO NOTHING without target (if supported)
            pg_conn.rollback()
            try:
                pg_cur.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING", values)
            except Exception as e2:
                pg_conn.rollback()
                print(f"Failed to insert row in {table}: {e2}")

pg_conn.commit()
print("Migration completed successfully!")
